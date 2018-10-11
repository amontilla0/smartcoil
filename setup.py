from setuptools import setup

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [ ]

setup_requirements = [ ]

test_requirements = [ ]


setup(
    author="Abraham R. Montilla Linares",
    author_email='amontilla0@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Full interface to automate a home-based fan coil unit with a Raspberry Pi. Notice that fan coil unit wiring may involve high voltage manipulation, any handling of this kind is under your own responsibility.",
    scripts=['bin/smartcoil'],
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='smartcoil',
    name='smartcoil',
    packages=find_packages(include=['smartcoil']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/amontilla0/smartcoil',
    version='0.1.0',
    zip_safe=False,
)
