import json
import redis

from functools import partial


def __cpu_transaction(function, semaphore_name):
    def wrapper(*args, **kwargs):
        args[0].wait(semaphore_name)
        try:
            result = function(*args, **kwargs)
        except Exception as e:
            raise e
        finally:
            args[0].notify(semaphore_name)
        return result
    return wrapper

cpu_acquire_transaction = partial(__cpu_transaction, semaphore_name="cpu-scheduler-semaphore")
cpu_transaction = partial(__cpu_transaction, semaphore_name="cpu-scheduler-admin-semaphore")


class CPUScheduler:

    cpu_list_names_map = {
        1024: "cpu-scheduler-ases-available-cpus",
        768 : "cpu-scheduler-dodrantis-available-cpus",
        512 : "cpu-scheduler-semissis-available-cpus",
        256 : "cpu-scheduler-quadrantis-available-cpus",
        0   : "cpu-scheduler-nulla-available-cpus",
    }

    cpu_list_names_reverse_map = {v: k for k, v in cpu_list_names_map.items()}

    cpu_status_map = "cpu-scheduler-available-cpus"

    cpu_scheduler_users_map = "cpu-scheduler-users"

    semaphore_names = ["cpu-scheduler-admin-semaphore", "cpu-scheduler-semaphore"]
    semaphore_names = ["cpu-scheduler-admin-semaphore", "cpu-scheduler-semaphore"]

    def __init__(self, host="localhost", port=6379, db=10):
        self.redis_connection = redis.StrictRedis(host=host, port=port, db=db)
        if not self.redis_connection.ping():
            raise Exception("Can not connect to redis server")

    def initialize_semaphores(self):
        for semaphore_name in CPUScheduler.semaphore_names:
            self.redis_connection.delete(semaphore_name)
            self.redis_connection.rpush(semaphore_name, 1)

    def wait(self, semaphore_name):
        self.redis_connection.blpop(semaphore_name, 0)

    def notify(self, semaphore_name):
        self.redis_connection.rpush(semaphore_name, 1)

    @cpu_transaction
    def remove_cpu_stats(self):
        cpu_lists = [CPUScheduler.cpu_list_names_map[256 * share] for share in range(5)]
        for cpu_list in cpu_lists:
            self.redis_connection.delete(cpu_list)
        self.redis_connection.delete(CPUScheduler.cpu_status_map)
        self.redis_connection.delete(CPUScheduler.cpu_scheduler_users_map)

    @cpu_transaction
    def add_cpu(self, cpu_number, share):
        cpu_list_name = CPUScheduler.cpu_list_names_map[share]
        cpu_status = {'available': share, 'users': []}
        self.redis_connection.hset(CPUScheduler.cpu_status_map, cpu_number, json.dumps(cpu_status))
        self.redis_connection.rpush(cpu_list_name, cpu_number)

    def add_ases_available_cpus(self, cpu_numbers):
        for cpu_number in cpu_numbers:
            self.add_cpu(cpu_number, 1024)

    @cpu_acquire_transaction
    def acquire_cpu(self, user, cpu_shares):
        for share in cpu_shares:
            if share not in CPUScheduler.cpu_list_names_map:
                return None
        cpu_numbers = []
        for share in cpu_shares:
            useful_share_names = [CPUScheduler.cpu_list_names_map[list_share] for list_share
                                  in sorted(CPUScheduler.cpu_list_names_map.keys())
                                  if list_share >= share]
            current_share, cpu_number = self.redis_connection.blpop(useful_share_names, 0)
            current_share = int(CPUScheduler.cpu_list_names_reverse_map[current_share.decode('utf8')])
            cpu_number = int(cpu_number)
            cpu_info = json.loads(self.redis_connection.hget(CPUScheduler.cpu_status_map, cpu_number).decode('utf8'))
            cpu_info['users'].append([user, share])
            cpu_info['available'] = current_share - share
            self.redis_connection.hset(CPUScheduler.cpu_status_map, cpu_number, json.dumps(cpu_info))
            self.redis_connection.rpush(CPUScheduler.cpu_list_names_map[cpu_info['available']], cpu_number)
            user_current_cpus = self.redis_connection.hget(CPUScheduler.cpu_scheduler_users_map, user)
            if not user_current_cpus:
                user_current_cpus = [cpu_number]
            else:
                user_current_cpus = json.loads(user_current_cpus.decode('utf8'))
                user_current_cpus.append(cpu_number)
            self.redis_connection.hset(CPUScheduler.cpu_scheduler_users_map, user, json.dumps(user_current_cpus))
            cpu_numbers.append(cpu_number)
        return cpu_numbers

    @cpu_transaction
    def release_cpu(self, user, cpu_number):
        cpu_info = json.loads(self.redis_connection.hget(CPUScheduler.cpu_status_map, cpu_number).decode('utf8'))
        current_list = CPUScheduler.cpu_list_names_map[cpu_info['available']]
        user_current_cpus = json.loads(self.redis_connection.hget(CPUScheduler.cpu_scheduler_users_map, user)
                                       .decode('utf8'))

        self.redis_connection.lrem(current_list, 0, cpu_number)

        removing_shares = [[share_user, share] for (share_user, share) in cpu_info['users'] if share_user == user]
        for [share_user, share] in removing_shares:
            cpu_info['users'].remove([share_user, share])
            cpu_info['available'] += share
            user_current_cpus.remove(cpu_number)

        self.redis_connection.hset(CPUScheduler.cpu_status_map, cpu_number, json.dumps(cpu_info))
        self.redis_connection.hset(CPUScheduler.cpu_scheduler_users_map, user, json.dumps(user_current_cpus))
        self.redis_connection.rpush(CPUScheduler.cpu_list_names_map[cpu_info['available']], cpu_number)

    @cpu_transaction
    def release_all_cpus(self, user):
        user_json = self.redis_connection.hget(CPUScheduler.cpu_scheduler_users_map, user)
        if not user_json:
            return
        user_current_cpus = json.loads(user_json.decode('utf8'))
        if not user_current_cpus:
            return

        for cpu_number in set(user_current_cpus):
            cpu_info = json.loads(self.redis_connection.hget(CPUScheduler.cpu_status_map, cpu_number).decode('utf8'))
            current_list = CPUScheduler.cpu_list_names_map[cpu_info['available']]

            self.redis_connection.lrem(current_list, 0, cpu_number)

            removing_shares = [[share_user, share] for (share_user, share) in cpu_info['users'] if share_user == user]
            for [share_user, share] in removing_shares:
                cpu_info['users'].remove([share_user, share])
                cpu_info['available'] += share

            self.redis_connection.hset(CPUScheduler.cpu_status_map, cpu_number, json.dumps(cpu_info))
            self.redis_connection.rpush(CPUScheduler.cpu_list_names_map[cpu_info['available']], cpu_number)

        self.redis_connection.hset(CPUScheduler.cpu_scheduler_users_map, user, json.dumps([]))

    def print_status(self):
        for semaphore_name in CPUScheduler.semaphore_names:
            print("semaphore `{}` status {}".format(
                semaphore_name, self.redis_connection.lrange(semaphore_name, 0, -1)))
        print()

        cpu_lists = [CPUScheduler.cpu_list_names_map[256 * share] for share in range(5)]
        for cpu_list in cpu_lists:
            print("CPUs in list `{}`:".format(cpu_list))
            print(" ".join([str(int(cpu_number)) for cpu_number in
                            self.redis_connection.lrange(cpu_list, 0, -1)]) + "\n")

        print("Cores Status:")
        core_names = sorted(self.redis_connection.hgetall(CPUScheduler.cpu_status_map))
        for core_name in core_names:
            print(str(int(core_name)) + " : " +
                  self.redis_connection.hget(CPUScheduler.cpu_status_map, core_name).decode('utf8'))
        print()

        print("Users:")
        users = sorted(self.redis_connection.hgetall(CPUScheduler.cpu_scheduler_users_map))
        for user in users:
            print(str(user.decode('utf8')) + " : " +
                  self.redis_connection.hget(CPUScheduler.cpu_scheduler_users_map, user).decode('utf8'))
        print()

