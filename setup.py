import re
from setuptools import setup


PCKG_NAME = 'pyjsaw'


def get_module_var(varname):
    regex = re.compile(fr"^{varname}\s*\=\s*['\"](.+?)['\"]", re.M)
    mobj = next(regex.finditer(open(f"{PCKG_NAME}/__init__.py").read()))
    return mobj.groups()[0]


#__author__ = get_module_var('__author__')
__license__ = 'MIT'
__version__ = get_module_var('__version__')


setup(
    name=PCKG_NAME,
    version=__version__,
    url="https://github.com/valq7711/websaw",
    license=__license__,
    #author=__author__,
    #author_email="valq7711@gmail.com",
    #maintainer=__author__,
    maintainer_email="valq7711@gmail.com",
    description=f"{PCKG_NAME} - funny IDE for websaw framework",
    platforms="any",
    keywords='python webapplication',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=[
        "websaw",
        "pydal",
    ],
    python_requires='>=3.7',
    packages=[PCKG_NAME],
    include_package_data=True,
)
