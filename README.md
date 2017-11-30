# NMOS Registry Query API Service

Provides a service implementing the NMOS Query API, specified in AMWA IS-04.

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

Unit tests are provided.  Currently these have hard-coded dummy/example hostnames, IP addresses and UUIDs.  You will need to edit the Python files under nmos-query/test/ to suit your needs and then "make test".

## Debian Packaging

Debian packaging files are provided for internal BBC R&D use.
These packages depend on packages only available from BBC R&D internal mirrors, and will not build in other environments. For use outside the BBC please use python installation method.
