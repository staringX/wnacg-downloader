#!/bin/bash
# 版本号管理脚本
# 用法: ./scripts/bump-version.sh [major|minor|patch]
# 示例: ./scripts/bump-version.sh patch  # 0.1.0 -> 0.1.1
#       ./scripts/bump-version.sh minor  # 0.1.0 -> 0.2.0
#       ./scripts/bump-version.sh major  # 0.1.0 -> 1.0.0

set -e

VERSION_FILE="VERSION"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# 检查参数
if [ $# -eq 0 ]; then
    echo "用法: $0 [major|minor|patch]"
    echo ""
    echo "版本号类型说明:"
    echo "  major - 大版本更新（不兼容的API变更）"
    echo "  minor - 小版本更新（新功能，向后兼容）"
    echo "  patch - 补丁版本（Bug修复，向后兼容）"
    exit 1
fi

BUMP_TYPE=$1

if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo "错误: 版本类型必须是 major、minor 或 patch"
    exit 1
fi

# 读取当前版本
if [ ! -f "$VERSION_FILE" ]; then
    echo "错误: 未找到 $VERSION_FILE 文件"
    exit 1
fi

CURRENT_VERSION=$(cat "$VERSION_FILE" | tr -d ' \n')
if [ -z "$CURRENT_VERSION" ]; then
    echo "错误: $VERSION_FILE 文件为空"
    exit 1
fi

# 解析版本号
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR=${VERSION_PARTS[0]}
MINOR=${VERSION_PARTS[1]}
PATCH=${VERSION_PARTS[2]}

# 递增版本号
case $BUMP_TYPE in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"

# 更新版本文件
echo "$NEW_VERSION" > "$VERSION_FILE"

# 显示变更
echo "✅ 版本号已更新"
echo "   旧版本: $CURRENT_VERSION"
echo "   新版本: $NEW_VERSION"
echo "   变更类型: $BUMP_TYPE"
echo ""
echo "下一步操作:"
echo "   1. 提交版本号变更: git add $VERSION_FILE && git commit -m \"chore: bump version to $NEW_VERSION\""
echo "   2. 创建Git tag: git tag -a v$NEW_VERSION -m \"Release version $NEW_VERSION\""
echo "   3. 推送代码和tag: git push origin main && git push origin v$NEW_VERSION"



