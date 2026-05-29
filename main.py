import os
import uuid
import traceback
import tempfile

import httpx

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain, Record
from astrbot.api.star import Context, Star
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core import logger


class Main(Star):
    """翻译 + TTS 语音合成插件（通用版，支持任意语言和多种 TTS 提供商）"""

    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.config = config

        # TTS 提供商选择
        self.tts_provider: str = config.get("tts_provider", "gpt_sovits")

        # GPT-SoVITS 配置
        self.gsv_api_url: str = config.get("gsv_api_url", "http://host.docker.internal:9880")
        self.ref_audio_path: str = config.get("ref_audio_path", "")
        self.prompt_text: str = config.get("prompt_text", "")
        self.prompt_lang: str = config.get("prompt_lang", "ja")

        # OpenAI TTS 配置
        self.openai_api_key: str = config.get("openai_api_key", "")
        self.openai_api_base: str = config.get("openai_api_base", "https://api.openai.com/v1")
        self.openai_tts_model: str = config.get("openai_tts_model", "tts-1")
        self.openai_tts_voice: str = config.get("openai_tts_voice", "alloy")

        # Fish Audio 配置
        self.fish_api_url: str = config.get("fish_api_url", "https://api.fish.audio")
        self.fish_api_key: str = config.get("fish_api_key", "")
        self.fish_model_id: str = config.get("fish_model_id", "")

        # Edge TTS 配置
        self.edge_tts_voice: str = config.get("edge_tts_voice", "ja-JP-NanamiNeural")

        # Azure TTS 配置
        self.azure_subscription_key: str = config.get("azure_subscription_key", "")
        self.azure_region: str = config.get("azure_region", "eastasia")
        self.azure_voice_name: str = config.get("azure_voice_name", "ja-JP-NanamiNeural")

        # Qwen3-TTS 配置
        self.qwen_api_key: str = config.get("qwen_api_key", "")
        self.qwen_voice_name: str = config.get("qwen_voice_name", "Chelsie")

        # 目标语言配置
        self.target_lang: str = config.get("target_lang", "ja")
        self.target_lang_name: str = config.get("target_lang_name", "日语")

        # 输出配置
        self.output_mode: str = config.get("output_mode", "dual_output")
        self.text_length_limit: int = config.get("text_length_limit", 200)
        self.request_timeout: int = config.get("request_timeout", 60)
        self.save_dir: str = config.get("save_dir", "")

        # 自定义翻译提示词（可选）
        self.custom_translation_prompt: str = config.get("custom_translation_prompt", "")

    @filter.on_decorating_result()
    async def translate_tts_decorate(self, event: AstrMessageEvent) -> None:
        result = event.get_result()
        if not result or not result.chain:
            return

        new_chain = []
        for comp in result.chain:
            if isinstance(comp, Plain) and comp.text and len(comp.text.strip()) > 1:
                text = comp.text.strip()
                if len(text) > self.text_length_limit:
                    new_chain.append(comp)
                    continue
                try:
                    # 第一步：翻译
                    translated_text = await self._translate(event, text)
                    if not translated_text:
                        logger.warning(f"[翻译TTS] 翻译失败，跳过: {text[:50]}")
                        new_chain.append(comp)
                        continue

                    logger.info(f"[翻译TTS] {text[:30]} -> {translated_text[:30]}")

                    # 第二步：TTS
                    audio_bytes = await self._call_tts(translated_text)
                    if audio_bytes:
                        audio_path = self._save_audio(audio_bytes)
                        record = Record(file=audio_path, url=audio_path, text=translated_text)
                        if self.output_mode == "voice_only":
                            new_chain.append(record)
                        else:
                            new_chain.append(comp)
                            new_chain.append(record)
                        logger.info(f"[翻译TTS] 语音合成成功 (提供商: {self.tts_provider})")
                    else:
                        new_chain.append(comp)
                except Exception:
                    logger.error(f"[翻译TTS] 处理出错:\n{traceback.format_exc()}")
                    new_chain.append(comp)
            else:
                new_chain.append(comp)

        result.chain = new_chain

    async def _translate(self, event: AstrMessageEvent, text: str) -> str | None:
        if self.custom_translation_prompt:
            system_prompt = self.custom_translation_prompt
        else:
            system_prompt = (
                f"请将以下文本翻译成{self.target_lang_name}。"
                f"只输出{self.target_lang_name}翻译结果，不要输出任何其他内容，不要解释，不要保留原文。"
                "翻译要自然流畅，适合语音对话场景。"
            )
        try:
            provider_id = await self.context.get_current_chat_provider_id(
                event.unified_msg_origin
            )
            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=text,
                system_prompt=system_prompt,
                max_tokens=200,
                temperature=0.3,
            )
            result = llm_resp.completion_text.strip()
            return result if result else None
        except Exception as e:
            logger.error(f"[翻译TTS] LLM 翻译失败: {e}")
            return None

    async def _call_tts(self, text: str) -> bytes | None:
        """根据配置的提供商调用对应的 TTS 服务"""
        providers = {
            "gpt_sovits": self._tts_gpt_sovits,
            "edge_tts": self._tts_edge_tts,
            "openai_tts": self._tts_openai,
            "fish_audio": self._tts_fish_audio,
            "azure_tts": self._tts_azure,
            "qwen_tts": self._tts_qwen,
        }

        provider_func = providers.get(self.tts_provider)
        if not provider_func:
            logger.error(f"[翻译TTS] 不支持的 TTS 提供商: {self.tts_provider}")
            return None

        return await provider_func(text)

    async def _tts_gpt_sovits(self, text: str) -> bytes | None:
        """GPT-SoVITS TTS"""
        body = {
            "text": text,
            "text_lang": self.target_lang,
            "ref_audio_path": self.ref_audio_path,
            "prompt_text": self.prompt_text,
            "prompt_lang": self.prompt_lang,
            "text_split_method": "cut3",
            "batch_size": 1,
            "media_type": "wav",
        }
        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            resp = await client.post(f"{self.gsv_api_url}/tts", json=body)
            resp.raise_for_status()
            return resp.content

    async def _tts_edge_tts(self, text: str) -> bytes | None:
        """Edge TTS (免费，无需 API Key)"""
        try:
            import edge_tts
            import asyncio

            communicate = edge_tts.Communicate(text, self.edge_tts_voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            return audio_data if audio_data else None
        except ImportError:
            logger.error("[翻译TTS] edge-tts 未安装，请运行: pip install edge-tts")
            return None
        except Exception as e:
            logger.error(f"[翻译TTS] Edge TTS 失败: {e}")
            return None

    async def _tts_openai(self, text: str) -> bytes | None:
        """OpenAI TTS"""
        if not self.openai_api_key:
            logger.error("[翻译TTS] OpenAI API Key 未配置")
            return None

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.openai_tts_model,
            "input": text,
            "voice": self.openai_tts_voice,
            "response_format": "wav",
        }
        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            resp = await client.post(
                f"{self.openai_api_base}/audio/speech",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            return resp.content

    async def _tts_fish_audio(self, text: str) -> bytes | None:
        """Fish Audio TTS"""
        if not self.fish_api_key:
            logger.error("[翻译TTS] Fish Audio API Key 未配置")
            return None

        headers = {
            "Authorization": f"Bearer {self.fish_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "text": text,
            "reference_id": self.fish_model_id,
            "format": "wav",
        }
        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            resp = await client.post(
                f"{self.fish_api_url}/v1/tts",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            return resp.content

    async def _tts_azure(self, text: str) -> bytes | None:
        """Azure TTS"""
        if not self.azure_subscription_key:
            logger.error("[翻译TTS] Azure 订阅密钥未配置")
            return None

        headers = {
            "Ocp-Apim-Subscription-Key": self.azure_subscription_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
        }
        ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{self.target_lang}'>
            <voice name='{self.azure_voice_name}'>{text}</voice>
        </speak>"""
        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            resp = await client.post(
                f"https://{self.azure_region}.tts.speech.microsoft.com/cognitiveservices/v1",
                headers=headers,
                content=ssml,
            )
            resp.raise_for_status()
            return resp.content

    async def _tts_qwen(self, text: str) -> bytes | None:
        """Qwen3-TTS (阿里通义千问语音合成)"""
        if not self.qwen_api_key:
            logger.error("[翻译TTS] Qwen API Key 未配置")
            return None

        headers = {
            "Authorization": f"Bearer {self.qwen_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "qwen3-tts",
            "input": {
                "text": text,
                "voice": self.qwen_voice_name,
            },
        }
        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            resp = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2speech/text-speech-generation",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            result = resp.json()
            audio_url = result.get("output", {}).get("audio", "")
            if audio_url:
                audio_resp = await client.get(audio_url)
                audio_resp.raise_for_status()
                return audio_resp.content
            return None

    def _save_audio(self, audio_bytes: bytes) -> str:
        save_dir = self.save_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        os.makedirs(save_dir, exist_ok=True)
        filename = f"tts_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(save_dir, filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
        return filepath
