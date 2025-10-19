# Checking the Docker Installation

After that, you can run Docker Hello World without root. To test it use the following command:

```shell
# After reboot
docker run hello-world
```

You will get a little happy message of Hello world, once again, but this time without root.

```
Hello from Docker!
This message shows that your installation appears to be working correctly.

To generate this message, Docker took the following steps:
1. The Docker client contacted the Docker daemon.
2. The Docker daemon pulled the "hello-world" image from the Docker Hub.
   (amd64)
3. The Docker daemon created a new container from that image which runs the
   executable that produces the output you are currently reading.
4. The Docker daemon streamed that output to the Docker client, which sent it
   to your terminal.

To try something more ambitious, you can run an Ubuntu container with:
$ docker run -it ubuntu bash

Share images, automate workflows, and more with a free Docker ID:
https://hub.docker.com/

For more examples and ideas, visit:
https://docs.docker.com/get-started/
```

## Troubleshooting Docker permission issues (Linux only)

If you get Docker permission error when running any Docker images, then likely,
you forgot to follow the steps to make Docker available without root or you need to _restart your Operating System_.

```
LibreLane> docker run hello-world
docker: Got permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock: Post "http://%2Fvar%2Frun%2Fdocker.sock/v1.24/containers/create": dial unix /var/run/docker.sock: connect: permission denied.
See 'docker run --help'.
LibreLane>
```

# Checking Installation Requirements

In order to check the installation, you can use the following commands:

```
docker --version
python3 --version
python3 -m pip --version
```

Successful outputs will look like this:

```
$ docker --version
Docker version 27.3.1, build ce12230
$ python3 --version
Python 3.10.5
$ python3 -m pip --version
pip 21.0 from /usr/lib/python3.10/site-packages/pip (python 3.10)
...
Once an environment has been created, you may wish to activate it, e.g. by
sourcing an activate script in its bin directory.
```

# Download and Install LibreLane

* Download LibreLane using PIP:

```sh
python3 -m pip install librelane
```

* Run a smoke test for LibreLane:

```sh
python3 -m librelane --dockerized --smoke-test
```

If the smoke test finishes successfully, congratulations. You're ready to use LibreLane.

```{note}
You can run simply invoke `python3 -m librelane --dockerized` without any arguments
to drop into an interactive shell inside the Docker environment, with your home
directory and your PDK root directory mounted.
```
