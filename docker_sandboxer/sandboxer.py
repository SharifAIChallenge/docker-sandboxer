from scheduler import CPUScheduler
from utils import run_compose_with_file
import yaml
from jinja2 import Environment, FileSystemLoader


class Sandbox(object):

    @property
    def _limit_validator(self):
        return {
            "cpu": Sandbox._validate_cpu,
            "memory": Sandbox._validate_int,
        }

    @staticmethod
    def _validate_cpu(cpu_limits):
        if isinstance(cpu_limits, int):
            cpu_limits = [cpu_limits, ]
        if not isinstance(cpu_limits, list):
            raise AssertionError("CPU limit should be either an int or a list of ints")
        for limit in cpu_limits:
            if limit not in CPUScheduler.cpu_list_names_map:
                raise AssertionError("Invalid CPU limit. CPU limit must be one of the followings: " +
                                     ",".join([key for key in CPUScheduler.cpu_list_names_map.keys()]))
        return cpu_limits

    @staticmethod
    def _validate_int(limit):
        if not isinstance(limit, int):
            raise AssertionError("Limit should be an int")
        return limit

    def __init__(self, **limits):
        self.limits = {}
        self.set_limits(**limits)

    def set_limits(self, **limits):
        for limit_name, limit_value in limits.items():
            self._set_limit(limit_name, limit_value)

    def _set_limit(self, limit_name, limit_desc):
        if not isinstance(limit_name, str):
            raise AssertionError("Limit name must be a string")
        validator = self._limit_validator.get(limit_name, None)
        if validator is not None:
            self.limits[limit_name] = validator(limit_desc)
        else:
            self.limits[limit_name] = limit_desc

    def get_limit(self, limit_name):
        return self.limits.get(limit_name, None)

    def get_all_limits(self):
        return self.limits


class Parser(object):

    def __init__(self, cpu_scheduler, yml_template_base, yaml_storage_folder=None):
        self.cpu_scheduler = cpu_scheduler
        self.jinja_environment = Environment(loader=FileSystemLoader(yml_template_base, followlinks=True))

        import os
        self.yaml_storage_folder = os.path.abspath(yaml_storage_folder)
        try:
            os.makedirs(self.yaml_storage_folder)
        except:
            pass

    @staticmethod
    def _find_and_replace_sandbox_ids(dictionary, sandbox_data):
                for key, value in dictionary.items():
                    if isinstance(value, dict):
                        Parser._find_and_replace_sandbox_ids(value, sandbox_data)

                for sandbox_id, sandbox_dict in sandbox_data.items():
                    if sandbox_id in dictionary:
                        dictionary.pop(sandbox_id)
                        dictionary.update(sandbox_dict)

    def create_yml_and_run(self, uid, yml_template_name, context):
        """
        :param uid: a unique id
        :param cpu_scheduler: an instance of CPUScheduler used for allocating CPU shares
        :param yml_template_dir: Directory of YAML template
        :param yml_template_name: YAML template name
        :param context: context used to parse the template.

        Compiles yml_template and runs docker-compose with it.
        You can add another key in some of your services called manager,
        This key is removed from the file which docker-compose will run with.
        However services that set this key's value as true will be knows as managers.
        All containers will be killed when all managers are stopped.
        If no manager is specified every container becomes a manager
        """

        context = context.copy()  # Making a copy from original dictionary since it's going to be modified below.

        make_manager_keyword = "make_manager"

        if make_manager_keyword in context:
            raise AssertionError("make_manager is a reserved keyword")
        context[make_manager_keyword] = "manager: true"

        sandboxes = {}

        for key, value in context.items():
            if isinstance(value, Sandbox):
                sandboxes[key] = value
                context[key] = "%s: sandbox_placeholder" % key

        template_string = self.jinja_environment.get_template(yml_template_name).render(context)
        compose_data = yaml.load(template_string)

        managers = []
        for container_name, data in compose_data.items():
            if "manager" in data:
                managers.append(container_name)
                data.pop("manager")

        # Each sandbox will be converted to a dictionary.
        # This variable holds a mapping from sandboxes ids to their corresponding dictionary.
        sandbox_data = {}

        # CPU shares should be reserved all at the same time.
        # Since order of cpu shares for a specific id doesn't matter,
        # it only suffices to know the id that a cpu share belongs to.

        # The i-th element of cpu_limits_ids is the id of i-th element of cpu_limits.
        cpu_limits_ids = []
        cpu_limits = []

        for sandbox_id, sandbox in sandboxes.items():
            sandbox_cpu_limit = sandbox.get_limit("cpu")
            if sandbox_cpu_limit is not None:
                for i in range(len(sandbox_cpu_limit)):
                    cpu_limits_ids.append(sandbox_id)
                cpu_limits += sandbox_cpu_limit
        try:
            cpu_shares = self.cpu_scheduler.acquire_cpu(uid, cpu_limits)
            print(cpu_limits)
            id_shares = {}  # Each id is mapped to a list containing shares assigned to that id
            for cpu_limits_id in cpu_limits_ids:
                id_shares[cpu_limits_id] = []

            for i in range(len(cpu_limits)):
                id_shares[cpu_limits_ids[i]].append(cpu_shares[i])
            for sandbox_id, sandbox in sandboxes.items():
                sandbox_data[sandbox_id] = sandbox.get_all_limits()
                if sandbox_id in id_shares:
                    sandbox_data[sandbox_id].pop("cpu")
                    sandbox_data[sandbox_id]["cpuset"] = ",".join([str(share_id) for share_id in id_shares[sandbox_id]])

            Parser._find_and_replace_sandbox_ids(compose_data, sandbox_data)

            # TODO: Memory should probably use the same approach as the CPU
            # TODO: i.e. we should wait until total requested memory is available and then divide it among the containers.
            import os
            yml_file_name = os.path.abspath("%s/%s.yml" % (self.yaml_storage_folder, uid))
            with open(yml_file_name, 'w') as yml_file:
                yml_file.write(yaml.dump(compose_data))
                yml_file.close()
                run_compose_with_file(uid, yml_file_name, managers)

        finally:
            self.cpu_scheduler.release_all_cpus(uid)


