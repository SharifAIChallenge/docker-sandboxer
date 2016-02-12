from setuptools import setup, find_packages
from docker_sandboxer import VERSION

setup(name='docker-sandboxer',
      version=VERSION,
      description='A sandbox using dockers container',
      url='https://github.com/SharifAIChallenge/AIC_game_runner',
      author='Sharif AIChallenge',
      author_email='sharif.aichallenge@gmail.com',
      license='BSD',
      packages=find_packages(),
      install_requires=[
            "redis >= 2.10.5, < 3",
            "PyYAML >=3.11, < 4",
            "Jinja2 >= 2.8, < 3",
            "docker-compose >= 1.5.2, < 2"
      ],
      zip_safe=False)