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
      zip_safe=False)