# BrandLoom marketplace listing handoff

This file is a manual listing aid for Agensi and AgentPowers. It is not part of
the public Skill ZIP and contains no account credentials or platform state.

## Common listing fields

- Display name / title: `BrandLoom`
- Slug: `brandloom`
- Category: `design`
- Type: `skill`
- Price: choose on the platform; this project does not assume a paid listing
- Repository: <https://github.com/yangjing6213-dev/project-brand-studio>

### Short description (English)

Use when a project needs a confirmed, repeatable brand-visual workflow from
project context, conversations, attachments, links, or supplied brand assets,
including logo cards, covers, bilingual variants, or scoped edits.

### Short description (简体中文)

适用于需要从项目上下文、对话、附件、链接或品牌素材出发，经过确认式流程生成或修改 LOGO 主视觉、封面、双语版本和品牌视觉变体的项目。

## Long description for AgentPowers (optional)

BrandLoom is a confirmation-first brand-visual Skill. It analyzes project
context and supplied assets, confirms copy, style, fonts, logo/IP choices,
rights, shot list, and output specifications, then composes deterministic
Pillow layouts around a host-generated base image. It keeps JSON state,
provenance, hashes, manifests, non-overwriting versioned outputs, and separate
logo-first and cover workflows. The runtime requires Python 3.12+ and
Pillow==12.3.0. Full image generation requires the host agent's built-in image
tool; no API key, external provider, recursive agent, or hidden network client
is used. Tool failure hard-stops. The bundled ENHE logo and IP references are
authorized for inclusion in this package, but that does not transfer ENHE
trademark or character rights to buyers or authorize presenting them as a
buyer's own brand. Users must confirm rights for their own uploaded assets.

## Upload notes

1. Upload the versioned `brandloom.zip` from the release directory supplied
   with this handoff.
2. For AgentPowers, select type `skill`; its ZIP form may require the title,
   description, category, and type to be entered manually.
3. For Agensi, keep the archive as one top-level `brandloom/` folder with
   `SKILL.md` at that folder's root. Do not upload `staging/`, `.brandloom/`,
   `dist/`, tests, or local generated outputs.
4. Let each platform perform its own security scan and manual review. This
   handoff does not claim an account, payout setup, or platform scan result.
