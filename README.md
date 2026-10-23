# SlipRank

给一个晶体方向，计算单轴拉伸或压缩下 α-Ti（HCP）和 β-Ti（BCC）滑移系、孪晶系的 Schmid 因子。若另外给出临界分切应力（CRSS），再计算分切应力和单晶 Sachs 屈服应力，并把排序表存下来。

原位力学和衍射分析里，经常要先判断某个取向会先开动哪一个滑移或孪晶。这一步通常是对几个晶面手算夹角。SlipRank 把这一步收成一次可重复的计算。

## 和已有项目的差别

2026-10-22 选题时读了 `TIDY_FOLDER_MAP.md` 的任务表和分类索引，并读了这些 README 的用途说明：

- [MuSlice](../MuSlice/README.md)：由能量、组成和透射率估算透射样品厚度。
- [anisoscope](../anisoscope/README.md)：由刚度矩阵检查弹性稳定性和方向弹性模量。
- [LatticeScope](../LatticeScope/README.md)：比较晶格畸变、晶粒取向和同步辐射峰位。
- [DirectionalPolar](../DirectionalPolar/README.md)：用 L、T、45° 三个宏观指标画面内性能极坐标图。
- [StrainLink](../StrainLink/README.md)：把逐帧衍射记录对应到一条参考应力–应变曲线。
- [StrainVista](../StrainVista/README.md)：把已有方位应变矩阵画成图。
- [p212-beamworks](../p212-beamworks/README.md)：整理 P21.2 探测器数据和实验记录。
- [AI-EPSC](../AI-EPSC/README.md)：衍射辅助的弹塑性自洽模型。
- [AI-Dislocation](../AI-Dislocation/README.md)：衍射线形和给定参数下的位错密度估计。滑移系参数是线形模型的输入，不是某个加载方向的 Schmid 排序。

这些项目都不输出“一个单轴方向上，各滑移系和孪晶系的 Schmid 因子、分切应力和 Sachs 应力”。

## 本版做什么，不做什么

做：

- 一个取向的单轴拉伸或压缩。
- HCP：基面 ⟨a⟩、柱面 ⟨a⟩、锥面 ⟨a⟩、{10-11}⟨11-23⟩、{11-22}⟨11-23⟩，以及 {10-12}、{11-22}、{10-11} 孪晶。
- BCC：{110}⟨111⟩、{112}⟨111⟩、{123}⟨111⟩。这一部分是几何排序，不是 β-Ti 螺位错的 non-Schmid 判据。
- 滑移取 Schmid 因子的绝对值。孪晶只保留与孪生剪切同号、且 m_active > 0 的一侧。
- 报告开头用中文写出优先家族、并列变体数、active Schmid 因子；给了 CRSS 才写 Sachs 应力。
- 方向可以写紧凑指数，例如 `0001`、`2-1-10`、`10-11`，也可以写 JSON。

不做：Bunge 或 Euler 角、EBSD、多晶 Taylor 或自洽平均、加工硬化、晶格转动、孪晶体积分数、FCC、内置实测 CRSS、衍射峰拟合、Rietveld。AI-EPSC 仍负责弹塑性自洽。

## 获取

仓库地址：https://github.com/D-sudoasd/SlipRank

克隆后进入仓库目录，双击 `run.cmd`。

## 启动

需要 Python 3.10 或更新版本，只用标准库。本机用 `py -3`（Python 3.13）跑通。

在 SlipRank 目录双击 `run.cmd`。它计算合成示例 `examples\c_axis_tension.json`，写入 `outputs\c_axis_tension\`，然后暂停，窗口不会马上关掉。

不需要暂停时：

```powershell
cd E:\Vibe_coding\SlipRank
.\run.cmd nopause
.\run-example.cmd
```

`run.cmd example` 在成功时不暂停，失败时暂停。`run.cmd ask` 只问一个方向，不填写 CRSS。

JSON 是可重复的路径：

```powershell
py -3 -m sliprank examples\c_axis_tension.json --out outputs\c_axis_tension
```

## 第一次使用

1. 双击 `run.cmd`，或运行上面的 `run-example.cmd`。
2. 窗口末尾的「先看这里」和 `outputs\c_axis_tension\report.md` 开头是同一段结论。
3. 同目录还有 `systems.csv`、`summary.json` 和 `ranking.svg`。图只是前 12 名的条形图，数值以报告和 CSV 为准。
4. 再运行一次。同一输入的四个文件内容相同。

这个示例的 `label` 是 `synthetic`。拉伸轴、400 MPa 和表里的 CRSS 都是构造的筛查整数，不是实测实验，也不是实测临界分切应力。c/a = 1.587 是 α-Ti 筛查用的常规比值，不是某块样品的实测点阵常数。

沿 [0001] 拉伸、σ = 400 MPa、且使用该示例 CRSS 时，报告给出：

- 优先家族是 {10-12} 拉伸孪晶（`twin_10_12`），6 个变体并列，不是单一优胜者。
- active Schmid 因子 0.498094，无量纲。
- τ = 199.2375 MPa。
- τ/CRSS = 1.9924。
- 取向 Sachs 屈服应力 200.7654 MPa。

代表变体的紧凑指数可能写成 `(-1012)[10-11]`。空格形式是 `(-1 0 1 2)[1 0 -1 1]`。全表里也有 `(10-12)[-1011]`。这些是同一族里符号约定不同的变体，Schmid 因子相同。

柱面 ⟨a⟩ 在示例里的 CRSS 最低（50 MPa），但沿 [0001] 拉伸时 m_active = 0，不进入 Sachs 估计。

不得把本示例的 50 MPa（柱面 ⟨a⟩ / `prismatic_a`）或 100 MPa（{10-12} / `twin_10_12`）写成、引用为或当作任何合金（包括 α-Ti）的临界分切应力。

## 只输入一个方向

`run.cmd ask`，或：

```powershell
py -3 -m sliprank --interactive --out outputs\interactive
```

按提示输入结构、拉伸或压缩、一个方向、可选的施加应力。CRSS 那一行直接回车。程序不会把一个数套到所有家族上，也不会编造 CRSS，因此这一路没有 Sachs 应力。分家族的 CRSS 仍写在 JSON 的 `crss_MPa` 里。交互输入的 `label` 记为 `user`。

HCP 接受 `0001`、`2-1-10`、`[2-1-10]`、`2 -1 -1 0`、`10-11`。BCC 接受 `001` 和 `0 0 1`。紧凑写法一位一个指数，负号属于下一位：`10-11` 是 [1 0 -1 1]，不是指数 10。`1001` 不满足 u+v+t=0，`0000` 是零矢量；两种都会点名错误，退出码为 2，并且不写结果文件。

## 公式、单位和适用条件

晶体直角坐标中，单位法向 n̂、单位剪切方向 ŝ、单位载荷方向 l̂：

```
m = (n̂ · l̂) (ŝ · l̂)          无量纲
τ / MPa = m_active × σ / MPa
σ_y / MPa = min(CRSS / m_active)
```

σ 为正，单位 MPa。拉或压由 `loading` 指定，不要把压写成负的 σ。

滑移：m_active = |m|。孪晶：拉伸时 m_active = m，压缩时 m_active = −m，并且只在该值大于 0 时开动。

{10-12}⟨10-11⟩ 的剪切方向取使 [0001] 伸长的一侧。{11-22}⟨11-23⟩ 和 {10-11}⟨10-12⟩ 取使 [0001] 缩短的一侧。

HCP 坐标：x ∥ [2-1-10]，y ∥ [01-10]，z ∥ [0001]。方向 [uvtw]（u+v+t=0），以 a 为单位：

```
x = (3/2) u
y = (√3/2) (u + 2v)
z = w (c/a)
```

晶面 (hkil)（h+k+i=0）的法向，以 1/a 为单位：

```
x = h
y = (h + 2k) / √3
z = l / (c/a)
```

沿 [0001] 拉伸时，(10-12)[-1011] 的 Schmid 因子化为

```
m = 1 / sqrt(2 + (c/a)^2 / 3 + 3 / (c/a)^2)
```

c/a = 1.587 时，m = 0.4980937…，报告里显示 0.498094。

BCC 只作为对照。[001] 拉伸时，(101)[11-1] 的 |m| = 1/√6。`examples\bcc_001_tension.json` 里 {110}⟨111⟩ 的示例 CRSS 取 50 MPa 时，Sachs 应力为 50×√6 = 122.4745 MPa，8 个 {110} 变体并列。这些整数同样不是实测 CRSS。

适用条件：一个取向的单轴拉伸或压缩；小应变，计算时不转动晶体；没有硬化和晶粒相互作用。CRSS 全部由输入给出。没给 CRSS 时只按 Schmid 因子排序，报告写明没有 Sachs 应力。

## 两个对照示例

都标成 `synthetic`。

`examples\a_axis_tension.json` 用与 c 轴示例相同的整数 CRSS，拉伸轴为 [2-1-10]。程序给出优先家族 `prismatic_a`，2 个变体并列，active Schmid 因子 0.433013，τ = 173.2051 MPa，Sachs 应力 115.4701 MPa。

`examples\schmid_only.json` 不提供 CRSS。沿 [0001] 拉伸时优先家族仍是 `twin_10_12`，active Schmid 因子仍是 0.498094，τ = 199.2375 MPa，没有 Sachs 应力。

## 换成自己的取向

复制 `examples\c_axis_tension.json`。把自己的数放进去时，把 `label` 改成 `user`。程序仍不判断这些数是否来自测量。

HCP 载荷用四个整数，且必须 u+v+t=0：

```json
"load": {"frame": "miller_bravais", "indices": [2, -1, -1, 0]}
```

也可以直接给晶体直角坐标，`xyz` 不必先归一化：

```json
"load": {"frame": "cartesian", "xyz": [1, 0, 1]}
```

同一套 CRSS 下比较几个方向时，另加非空的 `orientations` 数组，每项里的 `load` 覆盖顶层 `load`。这不是第一次使用要走的路径。

`c_over_a` 只用于 HCP。不写时用 1.587，报告会标明这是缺省筛查值。BCC 不要写 `c_over_a`。CRSS 可以只写一部分家族；没写的家族不进入 Sachs 比较。

## 指数怎么读

紧凑 Miller 指数每个数字是一位，负号属于紧随其后的那一位。`(10-12)` 是 (1 0 -1 2)，`[2-1-10]` 是 [2 -1 -1 0]，`[2-1-1-3]` 是 [2 -1 -1 -3]。报告在紧凑形式旁边给出空格形式。CSV 和 JSON 里有分号分隔的整数指数。Excel 可能把 `(-1012)` 当成公式，请用整数列。

## 输入出错时

程序把原因写到标准错误，退出码为 2，并且不写结果文件。例如零矢量：

```powershell
py -3 -m sliprank examples\bad_zero_load.json --out outputs\bad
```

错误是：`载荷方向是零矢量。请给出非零的 Miller、Miller–Bravais 或直角坐标方向。`

[1, 0, 0, 1] 会指出 `u+v+t=0` 不成立。CRSS 小于或等于 0 时，消息里有家族名和单位 MPa。`applied_stress_MPa` 必须大于 0。JSON 里的指数要写成整数数组：`[2-1-10]` 应写成 `[2, -1, -1, 0]`。

## 测试

```powershell
cd E:\Vibe_coding\SlipRank
py -3 -m unittest tests.test_schmid tests.test_friendly tests.test_wizard tests.test_indices_display -v
```

Schmid 因子的期望值来自 cos45°×cos45° = 1/2、1/√6，以及上面的 c 轴孪晶闭合式，不是把程序上次的输出抄回来。

## 完成情况

见 [COMPLETION.md](COMPLETION.md)。
