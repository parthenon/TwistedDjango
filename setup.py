#!/usr/bin/env python

from setuptools import setup, find_packages


setup(
    name='djangotwisted',
    version='0.1.6',
    description='Reusable websockets with Twisted in Django',
    author='Casey Beach',
    author_email='casey@parthenonsoftware.com',
    url='http://www.parthenonsoftware.com',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django'
    ]
)
