#!/bin/bash

# 遇到错误立即停止
set -e

# 定义颜色用于提示
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== 开始安装生产级 Docker 及 NVIDIA 环境 ===${NC}"

# 0. 检查是否为 Root 或有 sudo 权限
if [ "$EUID" -ne 0 ] && [ -z "$SUDO_USER" ]; then 
  echo -e "${RED}请使用 sudo 运行此脚本 (例如: sudo ./setup_docker.sh)${NC}"
  exit 1
fi

# 获取实际的非root用户名（因为脚本通常用sudo运行，直接用$USER会是root）
REAL_USER=${SUDO_USER:-$USER}

echo -e "${YELLOW}[1/6] 清理旧版本 Docker (如果有)...${NC}"
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do 
    apt-get remove -y $pkg || true
done

echo -e "${YELLOW}[2/6] 安装基础依赖并配置 Docker GPG 秘钥...${NC}"
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo -e "${YELLOW}[3/6] 添加 Docker 官方源...${NC}"
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update

echo -e "${YELLOW}[4/6] 安装 Docker Engine...${NC}"
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo -e "${YELLOW}[5/6] 配置 Docker 用户权限 (免 sudo)...${NC}"
if getent group docker > /dev/null 2>&1; then
    usermod -aG docker $REAL_USER
    echo -e "${GREEN}用户 $REAL_USER 已添加到 docker 组。${NC}"
else
    echo -e "${RED}Docker 组不存在，跳过此步骤。${NC}"
fi

echo -e "${YELLOW}[6/6] 安装 NVIDIA Container Toolkit...${NC}"
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt-get update
apt-get install -y nvidia-container-toolkit

# 配置 Docker 运行时以支持 NVIDIA
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}   安装完成！ Success!  ${NC}"
echo -e "${GREEN}==============================================${NC}"
echo -e "${YELLOW}重要提示：${NC}"
echo -e "1. 为了让 '用户组权限' 生效，你必须 ${RED}注销并重新登录${NC} 服务器。"
echo -e "   或者你可以现在运行命令: ${GREEN}newgrp docker${NC}"
echo -e "2. 验证 Docker 是否正常: ${GREEN}docker run hello-world${NC}"
echo -e "3. 验证 GPU 是否穿透成功: ${GREEN}docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi${NC}"
echo -e "   (注意: 第3步会自动下载较大的 CUDA 镜像，请耐心等待)"