由于这一部分涉及容器运行embedding模型，所以专门写了一个安装、配置docker的脚本：setup_docker_rag.sh。
它整合了清理旧版本、安装 Docker CE、配置当前用户权限以及安装 NVIDIA Container Toolkit 的所有标准步骤。
该脚本专为 Ubuntu 24.04 (及 22.04) 设计。

使用方法
将setup_docker_rag.sh上传到服务器上的任意目录，例如~/目录。

1.运行脚本：chmod +x setup_docker_rag.sh
2.运行脚本：./setup_docker_rag.sh

3.脚本执行后的关键检查
运行完脚本后，请务必执行以下步骤来验证环境是否适合跑 RAG：
刷新用户组：newgrp docker
测试显卡穿透（最关键的一步）： 运行下面的命令。如果你看到了显卡信息列表（类似于在宿主机运行 nvidia-smi 的输出），说明 TEI 和 vLLM 肯定能跑起来。
docker run --rm --gpus all ubuntu nvidia-smi
(注：如果你的机器上没有 ubuntu 镜像，它会自动下载。如果报错说找不到 nvidia-smi，请使用脚本末尾提示的 nvidia/cuda 镜像)

curl 127.0.0.1:8080/embed \
    -X POST \
    -d '{"inputs":"测试文本"}' \
    -H 'Content-Type: application/json'