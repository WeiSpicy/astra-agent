#!/bin/bash
IMAGE_NAME=weispicy/astra_agent_demo
CURRENT_VERSION=1.0.8

# 提取主版本号、次版本号和补丁号
MAJOR=$(echo "$CURRENT_VERSION" | awk -F. '{print $1}')
MINOR=$(echo "$CURRENT_VERSION" | awk -F. '{print $2}')
PATCH=$(echo "$CURRENT_VERSION" | awk -F. '{print $3}')

# 递增补丁号
NEW_PATCH=$((PATCH + 1))

# 检查是否需要进位（即补丁号达到 102, 次版本号 102）
if [ "$NEW_PATCH" -ge 102 ]; then
  NEW_PATCH=0
  MINOR=$((MINOR + 1)) # 进位到次版本号

  # 检查次版本号是否需要进位
  if [ "$MINOR" -ge 102 ]; then
    MINOR=0
    MAJOR=$((MAJOR + 1)) # 进位到主版本号
  fi
fi

# 移除旧版镜像
docker rmi "${IMAGE_NAME}:${CURRENT_VERSION}"

# 生成新版本号
NEW_VERSION="${MAJOR}.${MINOR}.${NEW_PATCH}"
echo "新版本号: $NEW_VERSION"
sed -i "s/^CURRENT_VERSION=.*/CURRENT_VERSION=${NEW_VERSION}/" deploy.sh

# 构建和推送镜像
echo "正在构建 & 推送镜像 [${IMAGE_NAME}:${NEW_VERSION}]"
docker build --no-cache -t "${IMAGE_NAME}:${NEW_VERSION}" . 
docker push "${IMAGE_NAME}:${NEW_VERSION}"

git add deploy.sh