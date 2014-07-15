# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = os.path.join(here, 'README.rst')

install_requirements = [
    'requests',
    # PyBit and dependencies
    'pybit',
    # 'psycopg2',
    # 'amqplib',
    'jsonpickle',
    'Pillow',
    ]
test_requirements = (
    'mock',
    )
# These requirements are specifically for the legacy module.
legacy_requirements = []

setup(
    name='roadrunners',
    version='1.0',
    author="Connexions/Rhaptos Team",
    author_email="info@cnx.org",
    long_description=open(README).read(),
    url='https://github.com/connexions/roadrunners',
    license='AGPL',  # See also LICENSE.txt
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requirements,
    tests_require = test_requirements,
    entry_points = """\
    """,
    test_suite='roadrunners.tests',
    )
