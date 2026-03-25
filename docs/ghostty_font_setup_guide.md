# Ghostty 字体配置简要教程

这份文档记录一次在 macOS 上为 Ghostty 配置中英文混排字体的思路和过程, 目标不是做完整字体评测, 而是留下一个可复用的操作路径

## 目标

希望在 Ghostty 里获得较好的中文, 英文和代码混排体验, 重点关注下面几件事

- 中文和英文放在一起时不要太突兀
- 终端里对齐要稳定, 尤其是表格, 缩进和代码块
- macOS 下安装和配置过程尽量简单

## 信息查询路径

这次主要查了两类信息

1. Ghostty 官方文档
2. 候选字体项目的官方说明

### 1. 查询 Ghostty 官方文档

先确认 Ghostty 的配置文件位置, 字体配置项名称, 以及是否支持字体 fallback

查询结论

- Ghostty 使用文本配置文件
- 常见配置文件位置是 `~/Library/Application Support/com.mitchellh.ghostty/config`
- 可以使用 `font-family` 和 `font-size`
- `font-family` 可以重复写, 用来做 fallback

参考

- https://ghostty.org/docs/config
- https://ghostty.org/docs/config/reference

### 2. 查询候选字体资料

为了找适合中文和英文混排的字体, 主要看了以下几个方向

- `Sarasa Gothic`
- `Maple Mono`
- `Noto Sans Mono CJK`

查询时重点关注的信息

- 是否明确支持简体中文和英文
- 是否适合编程或终端场景
- 是否强调中英文宽度协调, 2:1 宽度关系或等宽特性
- macOS 是否容易安装

## 查到的关键信息

### Sarasa Gothic

从项目资料和软件包说明里, 可以得到几个关键点

- 它面向 CJK 和拉丁字符混排
- 很适合编程场景
- 说明里强调了 CJK 字符与 ASCII 的宽度关系, 适合终端对齐
- 社区里常见推荐项就是 `Sarasa Term SC`

这意味着它比较符合"终端 + 中文 + 英文 + 代码"的组合需求

参考

- https://github.com/be5invis/Sarasa-Gothic
- https://packages.guix.gnu.org/packages/font-sarasa-gothic

### Maple Mono

从项目说明里查到

- `CN` 版本提供中文支持
- 明确强调中英文 2:1 宽度关系
- 偏重"程序员字体"的观感和终端体验

它也是很好的选择, 但默认更偏"风格化"和"编程字体感"

参考

- https://github.com/subframe7536/maple-font

### Noto Sans Mono CJK

它的优点主要是

- 覆盖稳
- 多语言支持完整
- 兼容性强

但就终端和代码观感来说, 通常没有前两个那么"编程场景导向"

参考

- https://notofonts.github.io/noto-docs/specimen/NotoSansMonoCJKsc/

## 决策依据

最后选择 `Sarasa Term SC`, 主要基于下面几个判断

- 它比通用型字体更偏终端和编程场景
- 它比很多纯英文字体 fallback 中文的方案更统一
- 对中文, 英文, 代码混排比较均衡
- 在 macOS 上可以直接通过 Homebrew 安装, 落地成本低

简单说

- 如果优先要"均衡稳妥", 选 `Sarasa Term SC`
- 如果优先要"更强烈的程序员字体风格", 可以考虑 `Maple Mono NF CN`
- 如果优先要"覆盖完整, 最省心", 可以考虑 `Noto Sans Mono CJK SC`

## 实际落地过程

### 1. 检查 Ghostty 是否已安装

```bash
which ghostty
```

### 2. 检查 Ghostty 配置文件是否存在

```bash
ls -la ~/Library/Application\ Support/com.mitchellh.ghostty/config
```

### 3. 安装字体

在 macOS 上使用 Homebrew 安装

```bash
brew install --cask font-sarasa-gothic
```

安装后字体文件会进入用户字体目录

### 4. 修改 Ghostty 配置

配置文件

`~/Library/Application Support/com.mitchellh.ghostty/config`

加入下面两行

```ini
font-family = "Sarasa Term SC"
font-size = 15
```

如果你已经有主题和配色配置, 直接追加即可, 不需要覆盖原有内容

### 5. 重载 Ghostty 配置

在 Ghostty 中使用

```text
Cmd+Shift+, 
```

## 最终结论

对于 macOS 上希望在 Ghostty 中获得较好中英文字体体验的用户, 这次的实操结论是

- 首选 `Sarasa Term SC`
- 配置简单
- 终端观感统一
- 中英文和代码混排表现比较稳

最终使用的配置如下

```ini
font-family = "Sarasa Term SC"
font-size = 15
```

## 可选补充

如果后续想进一步微调, 可以继续尝试

- 把 `font-size` 改成 `14` 或 `16`
- 对比 `Sarasa Term SC` 和 `Maple Mono NF CN`
- 使用 Ghostty 的多个 `font-family` 做 fallback, 但这种方式通常不如单一字体统一
