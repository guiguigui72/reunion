# ADR-0005：Python 版本锁定为 3.13

- 日期：2026-10-19
- 状态：已采纳

## 背景

用 `uv venv` 创建虚拟环境时，uv 默认选择了它能找到的最新版本：**Python 3.14.3**。
安装依赖失败：

```
Because chroma-hnswlib==0.7.6 has no usable wheels and chromadb==0.5.23
depends on chroma-hnswlib==0.7.6, we can conclude that chromadb==0.5.23 cannot be used.
```

根因：`chroma-hnswlib` 内部是 C++ 实现，必须针对每个 Python 版本编译出 wheel（预编译包）。
Python 3.14 太新，该版本还没有 3.14 的 wheel。而 `--only-binary :all:`
禁止从源码编译，于是无解。

系统 Python 是 **3.13.9**，装有同样版本的 `chromadb 0.5.23`，工作正常。

## 决定

项目统一使用 **Python 3.13**。

- 用 `uv venv --python 3.13` 显式指定版本
- 在项目根目录放 `.python-version`（内容为 `3.13`），让 uv 自动遵守

## 理由

依赖清单里的版本（2024 年底）与 3.13 匹配。

**最新 ≠ 最合适** —— 建虚拟环境时，Python 版本要跟着项目走，
不能跟着机器上的默认最新版走。

## 后果

- `uv venv` 不再需要手动指定版本
- 换机器或重装环境时，按 `requirements.txt` + `.python-version` 可以复现出同样的环境
- 更大的教训：`requirements.txt` **无法声明项目级 Python 版本**（它只是包清单）。
  项目级版本要求应写在 `pyproject.toml` 的 `requires-python` 或 `.python-version` 里
