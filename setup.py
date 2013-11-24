from setuptools import setup, find_packages
import sys, os


setup(name='lattr',
      version='0.1',
      description='Read it later Server end',
      classifiers=[],
      keywords='lattr readitlater read readability pocket instapaper',
      author='jiluo',
      author_email='weiqiyiji@gmail.com',
      url='https://github.com/weiqiyiji/lattr',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'Fabric',
          'Flask',
          'sqlalchemy',
          'gunicorn',
          'lxml',
          'beautifulsoup4'
      ],
      entry_points={
          'console_scripts': [
              'fab=fabric.main:main',
          ]
      })
