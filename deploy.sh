#!/bin/bash
# =============================================
#  微信公众号自动发布 - 部署脚本
#  将代码部署到远程服务器
# =============================================

# 配置信息（请修改为你的服务器信息）
SERVER_IP="43.139.159.58"
SERVER_USER="root"  # 修改为你的用户名
SERVER_PORT="22"
DEPLOY_PATH="/home/wechat_publish"  # 修改为你的部署路径

# 本地项目路径
LOCAL_PATH="c:/Users/Administrator/WorkBuddy/20260427080318/wechat_auto_publish"

echo "=============================================="
echo "  微信公众号自动发布 - 部署脚本"
echo "  服务器: $SERVER_IP"
echo "  用户: $SERVER_USER"
echo "  部署路径: $DEPLOY_PATH"
echo "=============================================="
echo ""

# 检查 SSH 连接
echo "[1/5] 检查 SSH 连接..."
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP "echo 'SSH 连接成功'" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ SSH 连接失败，请检查："
    echo "  1. 服务器 IP 是否正确"
    echo "  2. SSH 服务是否启动"
    echo "  3. 用户名和密码/密钥是否正确"
    exit 1
fi
echo "✅ SSH 连接成功"
echo ""

# 创建远程目录
echo "[2/5] 创建远程目录..."
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP "mkdir -p $DEPLOY_PATH"
if [ $? -ne 0 ]; then
    echo "❌ 创建目录失败"
    exit 1
fi
echo "✅ 远程目录创建成功"
echo ""

# 上传文件
echo "[3/5] 上传项目文件..."
FILES="main.py config.py requirements.txt"

for file in $FILES; do
    echo "  上传 $file..."
    scp -P $SERVER_PORT "$LOCAL_PATH/$file" $SERVER_USER@$SERVER_IP:$DEPLOY_PATH/
    if [ $? -ne 0 ]; then
        echo "  ❌ 上传 $file 失败"
        exit 1
    fi
done
echo "✅ 文件上传成功"
echo ""

# 安装依赖
echo "[4/5] 安装 Python 依赖..."
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP "cd $DEPLOY_PATH && pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/"
if [ $? -ne 0 ]; then
    echo "⚠️  依赖安装失败，请手动在服务器上执行："
    echo "  cd $DEPLOY_PATH"
    echo "  pip3 install -r requirements.txt"
else
    echo "✅ 依赖安装成功"
fi
echo ""

# 设置定时任务（可选）
echo "[5/5] 部署完成！"
echo ""
echo "=============================================="
echo "  部署完成！"
echo "=============================================="
echo ""
echo "下一步操作："
echo "1. SSH 登录服务器："
echo "   ssh $SERVER_USER@$SERVER_IP -p $SERVER_PORT"
echo ""
echo "2. 进入项目目录："
echo "   cd $DEPLOY_PATH"
echo ""
echo "3. 测试运行："
echo "   python3 main.py"
echo ""
echo "4. 设置定时任务（每天自动运行）："
echo "   crontab -e"
echo "   添加一行（每天早上8点运行）："
echo "   0 8 * * * cd $DEPLOY_PATH && python3 main.py >> publish_log.txt 2>&1"
echo ""
