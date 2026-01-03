# ZeroTerm（日本語版）

Headless Kali PTY over Web for Raspberry Pi Zero 2 W.
Version: v1

ZeroTerm は Pi Zero 2 W を「本物の Kali TTY」に変え、
Safari から操作するための最小構成の Web 端末です。
GUI もデスクトップもフレームワークも使いません。
Web は端末ケーブルという思想を守ります。

## Overview
- 実体 PTY を WebSocket で直結（コマンド制限なし）
- 最小構成の Web 端末（ANSI 色 + 基本 VT 操作）
- e-Paper でバッテリーとシステム状態を表示
- Status API + 電力プリセット
- systemd 前提、起動後すぐ使える

## Core Idea
「Web は端末ケーブルである」

ZeroTerm はコマンドを置き換えたり Web 化しません。
実際の PTY に生のバイトを中継します。

## What You Get
- ブラウザから使えるフルの Kali CLI
- フレームワークなしの HTML/CSS/JS 端末
- e-Paper の状態表示（バッテリー/通信/稼働）
- Windows での UI プレビュー（mock）

## Hardware / OS
- Raspberry Pi Zero 2 W（WH 可）
- Kali Linux Lite + systemd
- 管理用は内蔵 Wi-Fi、実験用は外部アダプタ推奨
- 任意: PiSugar バッテリー / Waveshare 2.13-inch e-Paper

## Quick Start
- 実機の導入は docs/SETUP_PI_ZERO.md へ。
- Windows で UI 確認: `python test\app.py`。

## Status API & Power Presets
- GET `/api/status` でバッテリーや電源状態を取得
- POST `/api/power` でプリセット切替
- CLI: `sudo zeroterm-power eco` / `balanced` / `performance` / `default`

## Implementation (Baseline)
- Python 3 標準ライブラリの PTY-over-WebSocket
- 最小構成の Web 端末クライアント
- systemd ユニット（端末 + e-Paper）
- 環境変数ベースの設定

## Documentation
- docs/ARCHITECTURE.md - システム構成と通信
- docs/SETUP_PI_ZERO.md - 導入手順と運用
- docs/CONFIG_EXAMPLES.md - 設定例
- docs/SECURITY.md - 運用時の注意

## License
MIT License
