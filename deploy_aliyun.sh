#!/bin/bash
# 阿里云一键部署脚本

echo "开始部署IT管理部智能助手..."

# 更新代码
cd /opt/dingtalk-robot
git pull

# 升级pip
pip3 install --upgrade pip

# 安装依赖
pip3 install -r requirements.txt

# 启动服务
nohup python3 -m src.app > /tmp/robot.log 2>&1 &

echo "等待服务启动..."
sleep 3

echo "=== 服务日志 ==="
cat /tmp/robot.log

echo ""
echo "=== 测试访问 ==="
curl -s http://localhost

echo ""
echo "部署完成！"
