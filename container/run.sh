docker run -it --rm \
  -v $(pwd)/container-uploads:/workspace/uploads \
  -v $(pwd)/container-config:/workspace/config \
  blazing-python-ds
