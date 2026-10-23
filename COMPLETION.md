# SlipRank 完成情况

检查时间：2026-10-23 +08。

## 已完成

- 单轴拉伸或压缩下，对一个晶体方向排出 HCP 或 BCC 滑移系和孪晶系。
- 输出无量纲 Schmid 因子、分切应力（MPa）和单晶 Sachs 屈服应力（MPa）。没给 CRSS 时只按 Schmid 因子排序，并写明没有 Sachs 应力。
- 滑移按双向，孪晶按单向。{10-12} 取伸长 [0001] 的剪切方向，{11-22} 和 {10-11} 取缩短 [0001] 的剪切方向。
- 报告开头和末尾有中文结论：优先家族、并列变体、active Schmid 因子；给了 CRSS 才写 Sachs 应力。
- 方向可以向导输入，例如 `0001`、`2-1-10`、`10-11`、`001`。向导不写入 CRSS。
- 结果写入 `report.md`、`systems.csv`、`summary.json` 和 `ranking.svg`。同一输入再跑一次，四个文件的内容相同。
- 非法输入给出点名的错误，退出码 2，不写结果文件。
- 双击 `run.cmd` 会在结束后暂停。`run-example.cmd` 和 `run.cmd nopause` 不暂停。
- 示例都标明 `synthetic`。示例整数 CRSS 不是实测值。
- 2026-10-23 08:21 +08 已推送到公开仓库 https://github.com/D-sudoasd/SlipRank 。默认分支 `main`，当时查到的 `visibility` 是 PUBLIC。

## 实际运行过

- `py -3 -m unittest tests.test_schmid tests.test_friendly tests.test_wizard tests.test_indices_display -v`：26 项通过。Schmid 期望值是 1/2、1/√6，以及 c 轴 {10-12}、{11-22} 的闭合式。
- `run-example.cmd` 连续启动两次，退出码都是 0。两次标准输出的二进制比较没有差异。`systems.csv`、`summary.json`、`ranking.svg` 与改结论文字之前的哈希相同。`report.md` 改为先写中文结论。
- 合成 c 轴示例：`twin_10_12` 六个变体并列，active Schmid 因子 0.498094，τ = 199.2375 MPa，Sachs 应力 200.7654 MPa。
- `examples/a_axis_tension.json`：优先家族 `prismatic_a`，2 个变体，active Schmid 因子 0.433013，Sachs 应力 115.4701 MPa。CRSS 仍是示例整数。
- `examples/schmid_only.json`：不提供 CRSS，Sachs 应力为空，优先家族仍是 `twin_10_12`。
- `--interactive` 输入 hcp、拉伸、`0001`、400 MPa、CRSS 回车：退出码 0，六个 `twin_10_12` 并列，没有 Sachs 应力。输入 `1001`：退出码 2，错误含 `u+v+t=0`，没有创建输出目录。
- `examples/bad_zero_load.json` 的标准错误含「零矢量」，没有创建输出目录。

## 仍影响使用

- 取向只能写 Miller、Miller–Bravais、晶体直角坐标，或向导接受的紧凑指数。不能直接读 Bunge 欧拉角或 EBSD 导出表。
- 没有内置实测 CRSS。排序依赖输入的 CRSS；示例里的整数只用于演示。
- 只处理一个取向的单轴载荷，不做多晶平均、硬化或晶格转动。
- 紧凑指数里每个数字是一位。负号属于下一位。分不清时看报告里的空格形式，或 CSV、JSON 里的整数指数列。
