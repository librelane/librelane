# Other Linux

## Installing Dependencies

For LibreLane you need a couple of tools installed:

* Docker version 25.0.5+
  * Docker post-installation steps for running without root.
* Git version 2.35+
* Python 3.10+ with pip and tkinter

Please install all of these dependencies using your package manager. Please note
that while alternative container services do work, they may not be officially
supported and are best-effort.

```{note}
We do test Podman in our CI, albeit, only for Ubuntu 24.04/26.04.

We welcome issues for other distributions.
```

### Installing Docker

First, install Docker following the steps provided [in this link](https://docs.docker.com/engine/install/).

Test if installation was successful:

```
sudo docker run hello-world
```

A successful installation of Docker looks like this:

```
Hello from Docker!
This message shows that your installation appears to be working correctly.

To generate this message, Docker took the following steps:
1. The Docker client contacted the Docker daemon.
2. The Docker daemon pulled the "hello-world" image from the Docker Hub. (amd64)
3. The Docker daemon created a new container from that image which runs the executable that produces the output you are currently reading.
4. The Docker daemon streamed that output to the Docker client, which sent it to your terminal.

To try something more ambitious, you can run an Ubuntu container with:
$ docker run -it ubuntu bash

Share images, automate workflows, and more with a free Docker ID:
https://hub.docker.com/

For more examples and ideas, visit:
https://docs.docker.com/get-started/
```

```{include} docker_no_root.md
:heading-offset: 2

```

```{include} _common.md
:heading-offset: 1

```
