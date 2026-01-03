# ZeroTerm（日本語版）

ZeroTerm は、Raspberry Pi Zero 2 W 専用に設計された
完全ヘッドレス・超軽量な Kali Linux ターミナルシステムです。

iPad（Safari）から Web 経由のみで操作できる
「実体のある Linux TTY」を提供します。

ディスプレイ、キーボード、デスクトップ環境、
および重いフレームワークは一切使用しません。

---

## 開発動機（Motivation）

近年の Linux やセキュリティツールは、
GUI 前提・高性能ハードウェア前提・複雑なフレームワーク依存
になりがちです。

ZeroTerm は、これとは真逆の思想で設計されています。

- Kali Linux をデスクトップOSではなくサービスOSとして扱う
- GUI・VNC・ウィンドウマネージャを完全排除
- Web は UI ではなく通信経路としてのみ使用
- バッテリー駆動・常時携帯可能な Linux 実験ノードを作る
- CUI を主役に据えた設計

ZeroTerm の目標は、
ネットワーク上に存在する本物の Linux 端末です。

---

## コアコンセプト

「Web は端末ケーブルである」

ZeroTerm は以下を行いません。

- CUI ツールを Web アプリ化しない
- コマンドを JSON や REST に変換しない
- 利用可能な Linux コマンドを制限しない
- サンドボックス化された疑似シェルを提供しない

代わりに：

- 実際の PTY（仮想端末）上でコマンドを実行
- 入力・出力を Web 経由で中継
- SSH と同等の操作感をブラウザで実現
- CUI ツールは一切改造しない

---

## 設計目標（Design Goals）

- 完全ヘッドレス運用（HDMI・キーボード・マウス不要）
- 100% CUI ベースの Kali Linux 環境
- Web ベースの端末操作（Safari 対応、アプリ不要）
- Raspberry Pi Zero 2 W の性能制約を前提とした軽量設計
- バッテリー駆動・常時携帯可能
- 役割の明確な分離（Web=通信、Linux=実行、CUI=操作）

---

## ZeroTerm が「できること」

- 実体のある Linux TTY を Web 越しに提供
- ヘッドレス Kali Linux ノードとして動作
- セキュリティ学習・検証・研究用途
- 通常の Linux コマンドが制限なく使用可能

使用例：

- apt install / apt build-dep
- ドライバ・カーネルモジュールのビルド
- ip, iw, rfkill, lsusb
- make を用いたコンパイル
- Kali Linux 標準の CUI ツール（wifite 等）

ZeroTerm 独自の制限レイヤーは存在しません。

---

## ZeroTerm が「しないこと」

- GUI を提供しない
- Web コマンドランチャーではない
- 制限付きシェルではない
- デスクトップ環境の代替ではない
- REST / JSON API サービスではない
- ブラウザ IDE ではない

---

## 想定ハードウェア構成

- Raspberry Pi Zero 2 W（WH でも可）
- Kali Linux（Lite）
- 外部 USB Wi-Fi アダプタ（実験用）
- 内蔵 Wi-Fi（管理・Web アクセス用）
- PiSugar2 バッテリーモジュール
- 2.13インチ ePaper ディスプレイ（状態表示専用）

ハードウェア制約は設計条件の一部です。

---

## 運用モデル

- 起動後、即座にサービス状態に入る
- 対話ログインは不要
- 中核機能は systemd サービスとして常駐
- 電源投入後、Web 経由で常に操作可能

---

## ePaper ディスプレイの思想

ePaper は操作画面ではありません。表示内容は以下に限定されます。

- システム状態（READY / RUNNING / DOWN）
- Web アクセス用 IP アドレス
- Wi-Fi 状態（SSID を含む）
- バッテリー残量（充電状態を含む）
- 稼働時間・温度・負荷（軽量なヘルスサマリ）

ログ表示や TTY 出力のミラーは行いません。

---

## ソフトウェア構成概要

- Kali Linux（Lite）
- X / Wayland / Desktop 不使用
- GUI ライブラリなし
- フロントエンドフレームワーク不使用
- 最小構成の HTML + JavaScript
- PTY ベースの端末バックエンド
- WebSocket 等の双方向通信
- systemd 管理サービス

---

## 利用上の注意

ZeroTerm は端末を提供するだけであり、用途や意図を制限しません。
教育・研究目的で利用し、各国の法令やネットワーク規約を遵守してください。
詳細は docs/SECURITY.md を参照してください。

---

## プロジェクトの状態

本リポジトリは ZeroTerm の設計思想と基盤構造を示すものです。
実装は以下を重視し、段階的に進めます。

- 正確性
- 単純さ
- 透明性

---

## 実装（ベースライン）

本リポジトリには、フレームワークなしの最小構成を含みます。

- Python 3 標準ライブラリによる PTY over WebSocket サービス
- 最小構成の HTML/CSS/JS 端末クライアント
- systemd 起動ユニット（端末 + ePaper 状態表示）
- 環境変数ベースの設定

---

## ドキュメント

- docs/ARCHITECTURE.md
- docs/SETUP_PI_ZERO.md
- docs/SECURITY.md
- docs/EPAPER.md
- docs/CONFIGURATION.md
- docs/PROTOCOL.md
- docs/CLIENT.md

---

## ライセンス

MIT License

---

## 一文要約

ZeroTerm は、Raspberry Pi Zero 2 W を完全ヘッドレスな Kali Linux ノードに変え、
iPad から Web 経由で本物の TTY を操作できる
超軽量セキュリティ実験デバイスです。
