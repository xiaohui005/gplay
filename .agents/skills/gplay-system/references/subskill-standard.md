# GPlay 子 Skill 标准

GPlay 只保留一个顶层 Skill：`gplay-system`。专项能力放在 `subskills/` 下，随着真实开发逐步形成。

## 什么时候创建子 Skill

满足下面任意条件再创建：

- 同类任务重复出现至少 2 次。
- 某个流程容易漏步骤，例如前端构建、后端重启、接口联调、权限验收。
- 某个领域有稳定规则，例如游戏列表、游戏详情、后台配置、用户权限、支付/积分/排行。
- 某个检查可以脚本化，且以后会反复使用。

不要为一次性任务创建子 Skill。

## 子 Skill 目录结构

```text
subskills/<name>/
  SKILL.md
  references/
  scripts/
```

只创建实际需要的目录。没有脚本就不要创建 `scripts/`。

## SKILL.md 要求

必须包含：

1. YAML frontmatter：`name` 和 `description`。
2. 什么时候使用。
3. 标准流程。
4. 验收标准。
5. 常见错误。
6. 需要读取的 reference 或运行的 script。

描述必须以 `Use when` 开头，方便自动发现。

## 子 Skill 命名

- 只用小写字母、数字、连字符。
- 名称要描述动作或领域。
- 示例：`frontend-workflow`、`backend-workflow`、`validation-gate`、`game-catalog`。

## 从经验到标准

每次发现新项目事实，先写入 `references/project-standards.md`。

当某类事实变成稳定流程，再升级为子 Skill：

1. 写失败或容易遗漏的场景。
2. 写最少规则解决这个遗漏。
3. 加入验收命令或脚本。
4. 运行 `scripts/audit_gplay_skill.py`。
