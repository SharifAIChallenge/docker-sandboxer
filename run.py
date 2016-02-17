from docker_sandboxer.sandboxer import Parser
from docker_sandboxer.scheduler import CPUScheduler
from docker_sandboxer.sandboxer import Sandbox


def main():
    cpu_scheduler = CPUScheduler()
    parser = Parser(cpu_scheduler, "./", "./out")
    uid = input()
    parser.create_yml_and_run(uid, "test.yml", {
        "qqq": {"sss": [{"web_sandbox": Sandbox(cpu=[])}]}
    }, 3)

if __name__ == "__main__":
    main()