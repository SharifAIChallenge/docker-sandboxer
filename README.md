# docker-sandboxer

There are three main classes in this package: CPUScheduler, Sandbox and Parser.
You may find the explanation for each of these classes below. An example is provided at the end of this documentation.

## CPUScheduler
This class handles CPU shares management. It uses redis database in order to store available CPU cores.
If you are going to apply a limit on CPU cores you will need a working redis database server which must be initialized 
by running the following static methods:
```
CPUScheduler.initialize_semaphores()
CPUScheduler.remove_cpu_stats()
```
Then you will need to add available CPU cores. In the following code `l` is considered as a list containing 
available cores number:
```
cpu_scheduler = CPUScheduler(REDIS_HOST, REDIS_PORT)
cpu_scheduler.add_ases_available_cpus(l)
```

In order to use Parser class you will need to create an instance of this class like above,
and pass it along to Parser's constructor.

## Sandbox
Instances of this class are used to store limits that are going to be applied on a container. You may either pass these limits directly to Sandbox's constructor or use the function update_limits. 
You may apply any limit that can be applied on a docker container in docker-compose YAML file. 
Additionally you may use the following keys:
```
 memory: Maximum memory the container may use in bytes
 swap: Maximum swap the container may use in bytes
 cpu: a list containing cpu shares required for this container
```
* In case you use memory or swap you may not use keyword mem_limit and/or memswap_limit.  
* In case you use cpu keyword you may not use cpuset keyword. 
* If you do not fulfill the above criteria(i.e. if you use the keywords that you shouldn't have), no exception will be raised but your provided values for those keywords will simply be ignored.

In order to apply an instance to a container you need to pass that instance in the dictionary provided to Parser with a custom name. For more information please see the example provided at the end of this documentation.  
 
## Parser
This class is used to parse a YAML file written in Jinja template's format and applying Sandbox instances.
The constructor takes three arguments:

* A CPUScheduler used for dividing cpu shares.
* A directory where your templates are stored.
* A directory where parsed templates will be stored. Parsed templates are stored for logging purposes.

Then you can use the function `create_yml_and_run` to parse and run a template which takes the following arguments in order:

* A unique identifier for these containers
* Name of the template to be parsed
* Dictionary used to parse this template
* Time to wait for containers to exit in seconds. It kills the containers after this time. If not provided or None is given, no time limit is applied.

## Example
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
