# 版本管理脚本

## 版本号管理

项目使用语义化版本（Semantic Versioning）格式：`MAJOR.MINOR.PATCH`

- **MAJOR**（大版本）：不兼容的API变更
- **MINOR**（小版本）：新功能，向后兼容
- **PATCH**（补丁版本）：Bug修复，向后兼容

## 使用方法

### 方式一：自动版本递增（默认行为，推荐用于日常开发）

**默认行为：每次push到main分支，如果没有指定tag，会自动递增补丁版本（patch，最后一位）**

```bash
# 正常提交代码即可，无需添加任何标记
git commit -m "feat: 添加新功能"
git push origin main

# GitHub Actions会自动：
# - 检测到没有tag
# - 自动递增补丁版本（0.1.0 -> 0.1.1）
# - 更新VERSION文件
# - 构建Docker镜像并打上版本标签
```

### 方式二：手动指定版本（推荐用于大版本变更）

使用Git tag手动指定版本号，tag优先级最高：

```bash
# 1. 创建tag（例如：大版本更新）
git tag -a v1.0.0 -m "Release version 1.0.0"

# 2. 推送tag（会自动触发Docker构建）
git push origin v1.0.0

# GitHub Actions会：
# - 检测到tag，使用tag作为版本号（1.0.0）
# - 不会自动递增版本号
# - 构建Docker镜像并打上版本标签
```

### 方式三：使用版本管理脚本（可选）

```bash
# 补丁版本（0.1.0 -> 0.1.1）
./scripts/bump-version.sh patch

# 小版本（0.1.0 -> 0.2.0）
./scripts/bump-version.sh minor

# 大版本（0.1.0 -> 1.0.0）
./scripts/bump-version.sh major

# 然后提交和创建tag
git add VERSION
git commit -m "chore: bump version to 0.1.1"
git tag -a v0.1.1 -m "Release version 0.1.1"
git push origin main
git push origin v0.1.1
```

## 版本号优先级

GitHub Actions 会按以下优先级选择版本号：

1. **Git tag**（最高优先级）：如果推送了tag（如 `v1.0.0`），使用tag作为版本号，**不会自动递增**
2. **自动递增补丁版本**：如果没有tag，默认自动递增补丁版本（patch，最后一位），例如 `0.1.0 -> 0.1.1`
3. **VERSION文件**：如果VERSION文件不存在，初始化为 `0.1.0`

## 版本号示例

- `0.1.0` - 初始版本
- `0.1.1` - Bug修复（使用 `[patch]` 标记）
- `0.2.0` - 新功能（使用 `[minor]` 标记）
- `1.0.0` - 重大更新（使用 `[major]` 标记或手动创建tag）

## 工作流程示例

### 日常开发（自动递增补丁版本）

```bash
# 1. 正常提交代码，无需添加任何标记
git commit -m "feat: 添加扫描本地文件功能"
git push origin main

# 2. GitHub Actions会自动：
#    - 检测到没有tag
#    - 自动递增补丁版本（0.1.0 -> 0.1.1）
#    - 更新VERSION文件并提交（使用[skip ci]避免循环触发）
#    - 构建Docker镜像并打上版本标签
```

### 大版本变更（手动指定tag）

```bash
# 1. 创建tag指定版本号（例如：重大更新）
git tag -a v1.0.0 -m "Release version 1.0.0"

# 2. 推送tag
git push origin v1.0.0

# 3. GitHub Actions会：
#    - 检测到tag，使用tag作为版本号（1.0.0）
#    - 不会自动递增版本号
#    - 构建Docker镜像并打上版本标签
```

## 注意事项

- **默认行为**：每次push到main分支，如果没有tag，会自动递增补丁版本（patch，最后一位），例如 `0.1.0 -> 0.1.1`
- **手动指定**：使用Git tag可以手动指定任意版本号（如大版本更新）
- **自动提交**：自动递增的版本号会通过 `[skip ci]` 提交VERSION文件，避免循环触发workflow
- **latest标签**：始终指向最新构建的版本
- **大版本变更**：建议使用Git tag手动指定，确保版本号准确

