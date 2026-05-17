# cc-forever-rules

Claude Code 行为规则系统，防止常见的 AI 编码失败——基于真实交互模式的系统分析，而非理论假设。

## 原则

| 原则 | 防止什么 |
|---|---|
| **防卡死** | 30分钟+ 零输出思考、决策循环、错误重试螺旋 |
| **完成验证** | 未完成的工作、虚假的"做完了"、未经测试的变更 |
| **简洁与精确改动** | 过度工程、推测性抽象、无关代码损坏、孤立导入 |
| **交互质量** | 方向错误执行、治标不治本、误判紧急程度、上下文丢失 |
| **执行规则** | 分批交付、说代替做、沟通不清晰 |

## 安装

```bash
/plugin marketplace add forever-218/cc-rules
/plugin install cc-forever-rules@cc-rules
```

然后在任何会话中使用：
```
/cc-rules
```

## 项目集成

如果不想每次手动调用技能，将 `CLAUDE.md` 中的规则复制到你项目的 `CLAUDE.md` 即可自动加载。

## 参考

- `load_rules.sh` — 独立脚本，可从任何 CC 窗口注入规则。运行 `bash load_rules.sh`。
- `CLAUDE.md` — 项目级安装的快速参考。
- [README.md](README.md) — English documentation.

## 许可证

MIT
