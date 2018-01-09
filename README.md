# NMOS Registry Query API Service

Provides a service implementing the NMOS Query API, specified in [AMWA IS-04](https://github.com/AMWA-TV/nmos-discovery-registration). This API allows querying of an IS-04 registry. This API can be used in conjunction with the [BBC's implementation of the Registration API](https://github.com/bbc/nmos-registration/). The BBC has also produced an open source implementation of the [IS-04 Node API](https://github.com/bbc/nmos-node).

For those wishing to experiment or familiarise themselves with the APIs the BBC has provided a joint reference implementation of IS-04 and IS-05 [here](https://github.com/bbc/nmos-joint-ri), which is readily installed using Vagrant and provides some basic user interfaces for interacting with the APIs.

This implementation was written by the BBC as part of our work on the IS-04 specification, and is research software. It has been open sourced to provide an example of the API, but has not been designed for use in production.

## Bugs and Contributions
Please file any bugs in the github issue tracker for this repository. We welcome contributions in the form of pull requests to this repository, but we would ask that you please take note of our contribution policy in [CONTRIBUTING.md](CONTRIBUTING.md).

## Installing with Python

Before installing this library please make sure you have installed the [NMOS Common Library](https://github.com/bbc/nmos-common), on which this API depends. The query API also requires [etcd](https://github.com/coreos/etcd) to be installed. For debain distributions this can be installed using apt:

```
sudo apt-get install etcd

```

Once all dependencies are satisfied run the following commands to install the API:

```
pip install setuptools
sudo python setup.py install
```

## Running the Query API

### Non-blocking

Run the following script to start the Query API in a non-blocking manner, and then stop it again at a later point:

```Python
    from nmosquery.service import QueryService

    service = QueryService()
    service.start()

    # Do something else until ready to stop

    service.stop()
```

### Blocking

It is also possible to run Query API in a blocking manner:

```python
from nmosquery.service import QueryService

service = QueryService()
service.run() # Runs forever
```

## Tests

Unit tests are provided.  Currently these have hard-coded dummy/example hostnames, IP addresses and UUIDs.  You will need to edit the Python files under nmos-query/test/ to suit your needs and then "make test". You will need to have [Python virtualenv](https://pypi.python.org/pypi/virtualenv) installed and in your system PATH.

## Debian Packaging

Debian packaging files are provided for internal BBC R&D use.
These packages depend on packages only available from BBC R&D internal mirrors, and will not build in other environments. For use outside the BBC please use python installation method.
