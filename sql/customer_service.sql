-- 金融智能客服系统 customer_service 库建表脚本（P1：5 张表）
SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS `customer_service`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `customer_service`;

-- 1. 会话表
CREATE TABLE IF NOT EXISTS `cs_session` (
  `session_id`   VARCHAR(64)  NOT NULL COMMENT '会话ID',
  `customer_no`  VARCHAR(64)  NOT NULL COMMENT '客户号',
  `channel_code` VARCHAR(32)  NOT NULL DEFAULT 'MOBILE_BANK' COMMENT '渠道编码',
  `status`       VARCHAR(16)  NOT NULL DEFAULT 'active' COMMENT '会话状态',
  `created_at`   DATETIME     NOT NULL,
  `updated_at`   DATETIME     NOT NULL,
  PRIMARY KEY (`session_id`),
  KEY `idx_cs_session_customer` (`customer_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话列表';

-- 2. 会话消息表
CREATE TABLE IF NOT EXISTS `cs_message` (
  `id`           BIGINT       NOT NULL AUTO_INCREMENT,
  `session_id`   VARCHAR(64)  NOT NULL COMMENT '会话ID',
  `sender`       VARCHAR(16)  NOT NULL COMMENT 'user/assistant',
  `message_type` VARCHAR(32)  NOT NULL DEFAULT 'text' COMMENT 'text/business_object',
  `content`      TEXT         NOT NULL COMMENT '消息内容',
  `object_json`  TEXT         NULL COMMENT '业务对象 JSON',
  `created_at`   DATETIME     NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_cs_message_session` (`session_id`, `id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话消息';

-- 3. 会话状态表（流程恢复依据）
CREATE TABLE IF NOT EXISTS `cs_session_state` (
  `session_id`  VARCHAR(64) NOT NULL,
  `customer_no` VARCHAR(64) NOT NULL,
  state_json  TEXT        NOT NULL COMMENT '完整对话状态 JSON',
  context_json TEXT        NULL COMMENT '客户上下文 JSON',
  `updated_at`  DATETIME    NOT NULL,
  PRIMARY KEY (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话状态';

-- 4. 知识库切块表（P2 使用，P1 先建）
CREATE TABLE IF NOT EXISTS `cs_kb_chunk` (
  `id`         BIGINT       NOT NULL AUTO_INCREMENT,
  `kb_type`    VARCHAR(32)  NOT NULL COMMENT 'faq/product/policy',
  `source`     VARCHAR(256) NOT NULL,
  `title`      VARCHAR(256) NULL,
  `content`    TEXT         NOT NULL,
  `embedding`  JSON         NOT NULL COMMENT '向量',
  `yn`         TINYINT      NOT NULL DEFAULT 1,
  `created_at` DATETIME     NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_cs_kb_type` (`kb_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库切块';

-- 5. 链路日志表（P4 使用，P1 先建）
CREATE TABLE IF NOT EXISTS `cs_trace` (
  `id`         BIGINT      NOT NULL AUTO_INCREMENT,
  `request_id` VARCHAR(64) NOT NULL,
  `session_id` VARCHAR(64) NOT NULL,
  `stage`      VARCHAR(32) NOT NULL COMMENT 'intent/rag/tool_call/reply/state',
  `detail`     JSON        NOT NULL,
  `cost_ms`    INT         NOT NULL DEFAULT 0,
  `created_at` DATETIME    NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_cs_trace_request` (`request_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话链路日志';

