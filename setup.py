from setuptools import setup, find_packages

setup(
    name = 'tiny_elephant',
    packages = find_packages(),
    version = '0.1.3',
    description = 'In memory based collaborative filtering',
    author = 'Hyeon-Mook Jerry Choi',
    author_email = 'chm073@gmail.com',
    url = 'https://github.com/kyunooh/tiny_elephant',
    download_url = 'https://github.com/kyunooh/tiny_elephant/archive/v0.1.3.tar.gz',
    keywords = ['clustering', 'collaborative filtering', 'redis', 'in memory based'],
    python_require = '>=3.4',
    zip_safe = False,
    install_requires=[
        'python-snappy',
        'redis',
        'datasketch',
        'simplejson'
    ],
    classifiers = [
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ]
)


