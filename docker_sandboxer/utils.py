from compose.cli.main import TopLevelCommand
import threading


def run_compose_with_file(project_name, yml_file, manager_services, timeout):

    class ContainerKiller(object):

        def __init__(self, project_description):
            self.project_description = project_description
            self.has_been_killed = False
            self.kill_lock = threading.Lock()

        def kill(self):
            self.kill_lock.acquire()
            if self.has_been_killed:
                return None
            self.has_been_killed = True
            # Kill all running containers
            command.dispatch(self.project_description + ["kill"], None)
            # Remove containers(Cleaning up)
            command.dispatch(self.project_description + ["rm", "--force"], None)
            self.kill_lock.release()

    """
        :param project_name: A name used to identify containers of this project
        :param yml_file; Path of YAML file which docker-compose is going to be run with.
        :param manager_services: list of services which are supposed to act as managers.
        Runs docker-compose and waits until manager containers stop. Kills all the container afterwards.
        Streams managers' logs to the output.
    """
    if not manager_services:
        manager_services = []

    command = TopLevelCommand()
    project_description = ["-f", [yml_file], "-p", project_name]
    # Start docker-compose as a daemon
    command.dispatch(project_description + ["up", "-d"], None)
    # Attach to manager container(s)' logs. Waits for manager container to stop.
    # if no service is mentioned as manager(i.e. manager_services is an empty list)
    # automatically attaches to all containers logs
    container_killer = ContainerKiller(project_description)

    timer = None
    if timeout:
        timer = threading.Timer(timeout, container_killer.kill)
    try:
        if timeout:
            timer.start()
        command.dispatch(project_description + ["logs"] + manager_services, None)
    finally:
        container_killer.kill()
        if timeout:
            timer.cancel()





