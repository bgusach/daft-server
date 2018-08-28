# coding: utf-8

import io
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

from setuptools import find_packages
from setuptools import setup


def read(*names, encoding='utf-8'):
    return io.open(
        join(dirname(__file__), *names),
        encoding=encoding,
    ).read()


setup(
    name='goattp',
    version='0.1.0',
    license='MPL-2.0',
    description='HTTP Server for learning purposes',
    long_description=read('README.rst'),
    author='Bor González Usach',
    author_email='bgusach@gmail.com',
    url='https://github.com/bgusach/goattp',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
    ],
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    install_requires=[
        # 'click',
    ],
    extras_require={
        # eg:
        #   'rst': ['docutils>=0.11'],
        #   ':python_version=="2.6"': ['argparse'],
    },
    entry_points={
        'console_scripts': [
            'goattp = goattp.cli:main',
        ]
    },
)
