方案一：Milvus Lite (最轻量，适合 Python 开发/原型验证)

如果你只是想在 Python 脚本或 Jupyter Notebook 中快速试用 Milvus，或者用于 RAG 的 Demo 开发，这是最简单的方法。它不需要 Docker，直接作为一个 Python 库运行。
适用场景：
 原型开发、本地测试、CI/CD 环境。
安装命令：
pip install milvus-lite

方案二：Milvus Standalone(最常用，适合本地开发/小规模生产)
这是标准的单机部署方式，适合在本地电脑（Mac/Windows/Linux）上完整体验 Milvus 的所有功能。
前置要求： 需已安装 Docker 和 Docker Compose。
安装步骤：
1.下载配置文件：
下载官方的 
docker-compose.yaml
 文件。
wget https://github.com/milvus-io/milvus/releases/download/v2.3.5/milvus-standalone-docker-compose.yml -O docker-compose.yml
(注：如果无法使用 wget，可以直接在浏览器访问上述链接保存文件)
2.启动服务：
sudo docker-compose up -d
3.验证状态：
sudo docker-compose ps
注意：本代码库里的demo代码都是用docker部署的，所以需要先启动milvus standalone服务。

方案三：Milvus Distributed(适合大规模生产环境)
如果你需要在生产环境中处理海量向量数据（亿级以上），建议使用 K8s 集群部署（Milvus Cluster）。
前置要求：
 一个 K8s 集群，已安装 Helm。
步骤：
1.添加 Milvus Helm 仓库：
helm repo add milvus https://zilliztech.github.io/milvus-helm/
helm repo update
2. 安装 Milvus：
helm install my-release milvus/milvus


无论你使用 Docker （方案二）还是 K8s（方案三） 安装服务端，你都需要客户端 SDK 来连接数据库。
pip install pymilvus