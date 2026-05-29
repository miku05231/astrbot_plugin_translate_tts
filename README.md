# AstrBot 翻译 + 多引擎语音合成插件

将 LLM 的回复自动翻译成目标语言，再通过多种 TTS 引擎合成语音。支持任意语言对，泛用性强。

## 功能

- 自动拦截 LLM 输出的文本
- 调用默认对话模型翻译成目标语言（日语、英语、韩语等任意语言）
- **多种 TTS 引擎支持：**
  - GPT-SoVITS（本地，需训练模型）
  - Edge TTS（免费，无需 API Key）
  - OpenAI TTS（云端，需 API Key）
  - Fish Audio（开源，支持语音克隆）
- 支持「文本+语音」和「仅语音」两种输出模式
- 可自定义翻译提示词，适配不同场景

## 前置要求

1. **AstrBot** >= 4.0
2. 至少配置一个 TTS 引擎（推荐 Edge TTS，无需额外配置）

## 安装

### 方法一：手动安装

1. 下载本项目
2. 将整个文件夹放入 AstrBot 的 `plugins/` 目录
3. 重启 AstrBot

### 方法二：Git 克隆

```bash
cd /path/to/AstrBot/plugins
git clone https://github.com/JxjxK/astrbot_plugin_translate_tts.git
```

### 安装 Edge TTS（可选）

如果使用 Edge TTS，需要安装依赖：

```bash
pip install edge-tts
```

## 配置

在 AstrBot Web 面板（`http://localhost:6185`）的插件管理中配置：

### 基础配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `tts_provider` | TTS 提供商 | `gpt_sovits` |
| `target_lang` | 目标语言代码 | `ja` |
| `target_lang_name` | 目标语言中文名称 | `日语` |
| `output_mode` | 输出模式 | `dual_output` |
| `text_length_limit` | 文本长度上限 | `200` |
| `request_timeout` | API 超时（秒） | `60` |
| `save_dir` | 语音文件保存目录 | 空（使用插件目录下 temp） |
| `custom_translation_prompt` | 自定义翻译提示词 | 空（使用默认提示词） |

### TTS 提供商配置

#### GPT-SoVITS

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `gsv_api_url` | GPT-SoVITS API 地址 | `http://host.docker.internal:9880` |
| `ref_audio_path` | 参考音频路径（宿主机路径） | - |
| `prompt_text` | 参考音频对应文本 | - |
| `prompt_lang` | 参考音频语言代码 | `ja` |

#### Edge TTS（推荐，免费）

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `edge_tts_voice` | Edge TTS 语音名称 | `ja-JP-NanamiNeural` |

常用 Edge TTS 语音：
- 日语：`ja-JP-NanamiNeural`、`ja-JP-MayuNeural`
- 英语：`en-US-JennyNeural`、`en-US-GuyNeural`
- 韩语：`ko-KR-SunHiNeural`
- 中文：`zh-CN-XiaoxiaoNeural`

#### OpenAI TTS

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `openai_api_key` | OpenAI API Key | - |
| `openai_api_base` | OpenAI API 地址 | `https://api.openai.com/v1` |
| `openai_tts_model` | TTS 模型 | `tts-1` |
| `openai_tts_voice` | TTS 语音 | `alloy` |

OpenAI TTS 语音选项：`alloy`、`echo`、`fable`、`onyx`、`nova`、`shimmer`

#### Fish Audio

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `fish_api_url` | Fish Audio API 地址 | `https://api.fish.audio` |
| `fish_api_key` | Fish Audio API Key | - |
| `fish_model_id` | 语音模型 ID | - |

#### Azure TTS

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `azure_subscription_key` | Azure 订阅密钥 | - |
| `azure_region` | Azure 区域 | `eastasia` |
| `azure_voice_name` | Azure 语音名称 | `ja-JP-NanamiNeural` |

常用 Azure 区域：
- `eastasia` - 东亚
- `japaneast` - 日本东部
- `westus` - 美国西部
- `westeurope` - 西欧

### 语言代码参考

| 语言 | 代码 | 名称 |
|------|------|------|
| 日语 | `ja` | 日语 |
| 英语 | `en` | 英语 |
| 韩语 | `ko` | 韩语 |
| 法语 | `fr` | 法语 |
| 德语 | `de` | 德语 |
| 西班牙语 | `es` | 西班牙语 |

### 输出模式

- `dual_output`：同时输出原文文本和翻译语音
- `voice_only`：仅输出翻译语音

## 工作流程

```
用户发送消息
    ↓
LLM 生成回复
    ↓
插件拦截文本
    ↓
调用 LLM 翻译成目标语言
    ↓
调用配置的 TTS 引擎合成语音
    ↓
输出：原文文本 + 目标语言语音
```

## Docker 部署

如果 AstrBot 运行在 Docker 中，使用 GPT-SoVITS 时需要：

1. `docker-compose.yml` 中添加网络访问：
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   ```

2. GPT-SoVITS 服务运行在宿主机上，端口 9880

使用 Edge TTS 或 OpenAI TTS 时无需额外 Docker 配置。

## 示例配置

### Edge TTS 日语（推荐，免费）

```yaml
tts_provider: "edge_tts"
edge_tts_voice: "ja-JP-NanamiNeural"
target_lang: "ja"
target_lang_name: "日语"
output_mode: "dual_output"
```

### Edge TTS 英语

```yaml
tts_provider: "edge_tts"
edge_tts_voice: "en-US-JennyNeural"
target_lang: "en"
target_lang_name: "英语"
output_mode: "dual_output"
```

### OpenAI TTS

```yaml
tts_provider: "openai_tts"
openai_api_key: "sk-your-api-key"
openai_tts_model: "tts-1"
openai_tts_voice: "nova"
target_lang: "ja"
target_lang_name: "日语"
output_mode: "dual_output"
```

### GPT-SoVITS

```yaml
tts_provider: "gpt_sovits"
gsv_api_url: "http://host.docker.internal:9880"
ref_audio_path: "your-reference-audio.ogg"
prompt_text: "参考音频中的文本内容"
prompt_lang: "ja"
target_lang: "ja"
target_lang_name: "日语"
output_mode: "dual_output"
```

### Fish Audio

```yaml
tts_provider: "fish_audio"
fish_api_url: "https://api.fish.audio"
fish_api_key: "your-fish-api-key"
fish_model_id: "your-model-id"
target_lang: "ja"
target_lang_name: "日语"
output_mode: "dual_output"
```

### Azure TTS

```yaml
tts_provider: "azure_tts"
azure_subscription_key: "your-azure-subscription-key"
azure_region: "eastasia"
azure_voice_name: "ja-JP-NanamiNeural"
target_lang: "ja"
target_lang_name: "日语"
output_mode: "dual_output"
```

## 常见问题

### Q: 翻译结果不自然
A: 可以在 `custom_translation_prompt` 中自定义翻译提示词，加入更多角色设定或风格要求。

### Q: 语音合成失败
A: 检查对应的 TTS 服务是否正常运行，配置是否正确。

### Q: 只想输出语音不要文本
A: 将 `output_mode` 改为 `voice_only`。

### Q: 如何切换到其他语言
A: 修改 `target_lang`（语言代码）和 `target_lang_name`（语言名称），并选择对应的 TTS 语音。

### Q: Edge TTS 安装失败
A: 确保已安装 edge-tts：`pip install edge-tts`。如果在 Docker 中使用，需要进入容器安装。

### Q: 哪个 TTS 引擎最好
A: 
- **免费推荐**：Edge TTS，无需 API Key，质量不错
- **高质量推荐**：OpenAI TTS 或 GPT-SoVITS（需训练）
- **语音克隆**：GPT-SoVITS 或 Fish Audio

## License

MIT
