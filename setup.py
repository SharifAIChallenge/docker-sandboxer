from setuptools import setup, find_packages
from docker_sandboxer import VERSION
from pip.req import parse_requirements

install_reqs = parse_requirements("requirements.txt")
reqs = [str(ir.req) for ir in install_reqs]

setup(name='docker-sandboxer',
      version=VERSION,
      description='A sandbox using dockers container',
      url='https://github.com/SharifAIChallenge/AIC_game_runner',
      author='Sharif AIChallenge',
      author_email='sharif.aichallenge@gmail.com',
      license='BSD',
      packages=find_packages(),
      install_reqs=reqs,
      zip_safe=False)