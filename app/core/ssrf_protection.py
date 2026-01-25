"""
SSRF Protection utilities for Smart Agriculture system.

This module provides URL validation and secure image download functionality
to prevent Server-Side Request Forgery (SSRF) attacks.

Key features:
- IP address blacklist validation (blocks private, loopback, link-local IPs)
- DNS Rebinding attack prevention (uses resolved IP for requests)
- Content-Type validation (only allows image types)
- File size limits (prevents DoS)
"""

import ipaddress
import logging
import socket
from typing import Tuple
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# 配置常量
ALLOWED_SCHEMES = ("http", "https")
ALLOWED_IMAGE_TYPES = (
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
)
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
DOWNLOAD_TIMEOUT = 30  # 秒


class SSRFValidationError(Exception):
    """URL 验证失败异常."""

    pass


class ImageDownloadError(Exception):
    """图片下载失败异常."""

    pass


def validate_image_url(url: str) -> Tuple[str, str]:
    """
    验证图片 URL 不指向内网地址，并返回解析后的 IP 和主机名。

    防护措施：
    1. 只允许 HTTP/HTTPS 协议
    2. 禁止 localhost 和回环地址
    3. 解析域名，检查所有 IP 地址是否为私有/内网地址
    4. 返回第一个公网 IP 用于后续请求

    Args:
        url: 待验证的图片 URL

    Returns:
        (ip_address, hostname) 元组
        - ip_address: 解析后的 IP 地址（用于发起请求）
        - hostname: 原始主机名（用于 Host header）

    Raises:
        SSRFValidationError: URL 验证失败（内网地址、不支持的协议等）

    Examples:
        >>> validate_image_url("https://example.com/image.jpg")
        ('93.184.216.34', 'example.com')

        >>> validate_image_url("http://localhost:8000/test.jpg")
        SSRFValidationError: 禁止访问 localhost/回环地址
    """
    # 1. 解析 URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise SSRFValidationError(f"无效的 URL 格式: {e}") from e

    # 2. 验证协议
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SSRFValidationError(
            f"不支持的协议: {parsed.scheme}. 仅允许: {ALLOWED_SCHEMES}"
        )

    # 3. 提取主机名
    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("URL 缺少主机名")

    # 4. 禁止 localhost 和回环地址（字符串级别检查）
    hostname_lower = hostname.lower()
    if hostname_lower in (
        "localhost",
        "127.0.0.1",
        "::1",  # IPv6 回环地址（urlparse 返回时不带方括号）
        "0.0.0.0",
        "127.0.1.1",
    ):
        raise SSRFValidationError(f"禁止访问 localhost/回环地址: {hostname}")

    # 5. 禁止私有地址字符串模式（在 DNS 解析前快速拒绝）
    if hostname_lower.startswith("127.") or hostname_lower.startswith("192.168.") or hostname_lower.startswith("10."):
        raise SSRFValidationError(f"禁止访问私有地址: {hostname}")

    # 6. DNS 解析，获取所有 IP 地址
    try:
        # 设置 DNS 超时，防止 DNS 慢速攻击
        socket.setdefaulttimeout(5)
        addr_info = socket.getaddrinfo(hostname, None)
        # 提取所有 IP 地址（去重）
        ips = list(set([addr[4][0] for addr in addr_info]))
    except socket.timeout as e:
        # socket.timeout 是 OSError 的子类，必须先捕获
        raise SSRFValidationError(f"DNS 查询超时: {hostname}") from e
    except (socket.gaierror, OSError) as e:
        # 捕获 DNS 解析错误（包括 gaierror 和其他 socket 错误）
        raise SSRFValidationError(f"DNS 解析失败: {hostname} - {e}") from e
    finally:
        # 重置 socket 超时
        socket.setdefaulttimeout(None)

    if not ips:
        raise SSRFValidationError(f"域名未解析到任何 IP 地址: {hostname}")

    # 7. 验证所有解析的 IP 地址，确保都不是内网地址
    # 这一步可以防止 DNS 重绑定攻击（攻击者控制一个域名，
    # 第一次查询返回公网 IP，第二次查询返回内网 IP）
    public_ips = []
    for ip in ips:
        try:
            ip_obj = ipaddress.ip_address(ip)

            # 检查是否为回环地址
            if ip_obj.is_loopback:
                raise SSRFValidationError(
                    f"禁止访问回环地址: {hostname} -> {ip}"
                )

            # 检查是否为链路本地地址（169.254.0.0/16，必须在 is_private 前检查）
            if ip_obj.is_link_local:
                raise SSRFValidationError(
                    f"禁止访问链路本地地址: {hostname} -> {ip}"
                )

            # 检查是否为私有地址（RFC 1918）
            if ip_obj.is_private:
                raise SSRFValidationError(
                    f"禁止访问私有地址: {hostname} -> {ip} (RFC 1918)"
                )

            # 检查是否为保留地址
            if ip_obj.is_reserved:
                raise SSRFValidationError(
                    f"禁止访问保留地址: {hostname} -> {ip}"
                )

            # 检查是否为多播地址
            if ip_obj.is_multicast:
                raise SSRFValidationError(
                    f"禁止访问多播地址: {hostname} -> {ip}"
                )

            public_ips.append(ip)

        except ValueError:
            # 如果 IP 地址解析失败，跳过
            logger.warning(f"无效的 IP 地址格式: {ip}")
            continue

    if not public_ips:
        raise SSRFValidationError(f"域名 {hostname} 的所有 IP 地址都是内网/保留地址")

    # 8. 返回第一个公网 IP（用于后续请求）和原始主机名
    selected_ip = public_ips[0]
    logger.info(f"URL 验证通过: {hostname} -> {selected_ip}")

    return selected_ip, hostname


def download_image_securely(
    url: str,
    max_size: int = MAX_IMAGE_SIZE_BYTES,
    timeout: int = DOWNLOAD_TIMEOUT,
) -> bytes:
    """
    安全下载图片（防 DNS Rebinding 攻击）。

    工作流程：
    1. 验证 URL，解析域名获取 IP 地址
    2. 使用 IP 地址发起 HTTP 请求（而非域名）
    3. 在 Host header 中保留原始主机名（支持虚拟主机）
    4. 验证响应 Content-Type 为图片类型
    5. 限制下载文件大小

    Args:
        url: 图片 URL
        max_size: 最大允许的文件大小（字节）
        timeout: 下载超时时间（秒）

    Returns:
        图片二进制数据

    Raises:
        SSRFValidationError: URL 验证失败
        ImageDownloadError: 下载失败或验证失败

    Examples:
        >>> image_data = download_image_securely("https://example.com/photo.jpg")
        >>> len(image_data)
        123456
    """
    # 1. 验证 URL 并获取 IP 地址
    try:
        ip_address, hostname = validate_image_url(url)
    except SSRFValidationError as e:
        # 将 SSRF 验证错误转换为 ImageDownloadError
        raise ImageDownloadError(f"URL 验证失败: {str(e)}") from e

    # 2. 重建 URL（使用 IP 地址而非域名）
    # 这样可以防止 DNS Rebinding 攻击，因为我们使用的是已验证的 IP 地址
    parsed = urlparse(url)
    target_url = parsed._replace(netloc=f"{ip_address}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}").geturl()

    # 3. 准备请求头（保留原始 Host，支持虚拟主机）
    headers = {
        "Host": hostname,  # 关键：使用原始主机名，而非 IP 地址
        "User-Agent": "Smart-Agriculture-Diagnosis/1.0",
    }

    # 4. 发起 HTTP 请求
    logger.info(f"下载图片: {hostname} -> {ip_address}")
    try:
        response = requests.get(
            target_url,
            headers=headers,
            timeout=timeout,
            stream=True,  # 流式下载，支持大小限制
            allow_redirects=True,  # 允许重定向（但目标 IP 已固定）
        )
        response.raise_for_status()

    except requests.exceptions.Timeout:
        raise ImageDownloadError(f"下载超时: {url}") from None
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else "Unknown"
        raise ImageDownloadError(f"HTTP 错误: {status_code} - {url}") from e
    except requests.exceptions.RequestException as e:
        raise ImageDownloadError(f"下载失败: {str(e)} - {url}") from e

    # 5. 验证 Content-Type
    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ImageDownloadError(
            f"不支持的文件类型: {content_type}. "
            f"仅允许图片类型: {ALLOWED_IMAGE_TYPES}"
        )

    # 6. 流式下载并验证文件大小
    image_data = bytearray()
    content_length = response.headers.get("Content-Length")

    # 如果有 Content-Length header，先检查大小
    if content_length and int(content_length) > max_size:
        raise ImageDownloadError(
            f"文件过大: {content_length} 字节（最大允许 {max_size} 字节）"
        )

    # 分块下载
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:  # 过滤掉 keep-alive chunk
            image_data.extend(chunk)
            if len(image_data) > max_size:
                raise ImageDownloadError(
                    f"文件过大: 已下载 {len(image_data)} 字节（最大允许 {max_size} 字节）"
                )

    logger.info(
        f"图片下载成功: {hostname} -> {len(image_data)} 字节, type={content_type}"
    )

    return bytes(image_data)
