# docker-sandboxer

You may find a sample usage below:

**test.py**
```
from docker_sandboxer.sandbox import Sandbox, Parser
from docker_sandboxer.scheduler import CPUScheduler

sandbox = Sandbox(memory=100000000)
sandbox.update_limits(cpu=[1024, 512], swap=0, )

cpu_scheduler = CPUScheduler("localhost", 6379)
parser = Parser(cpu_scheduler, "templates/", "yaml_logs/")
parser.create_yml_and_run("some_unique_id", "compile.yml", {
    "compiler_sandbox": sandbox,
    "server_image": redis
})
```

**template.yml**
```
server:
    image: {{ server_image }}
compiler:
    image: compiler
    {{ compiler_sandbox }}
```
