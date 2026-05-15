-- Creates the two tables missing in production for the review feature.
-- Run on the server with:
--   mysql -u root -p discount_db < fix_review_tables.sql
-- Safe to re-run: IF NOT EXISTS guards against duplicate creation.

CREATE TABLE IF NOT EXISTS `services_eventreview` (
  `id`             bigint        NOT NULL AUTO_INCREMENT,
  `rating`         smallint unsigned NOT NULL,
  `mark`           varchar(10)   NOT NULL,
  `title`          varchar(200)  NOT NULL,
  `comment`        longtext      NOT NULL,
  `is_approved`    tinyint(1)    NOT NULL,
  `is_flagged`     tinyint(1)    NOT NULL,
  `flag_reason`    varchar(255)  NOT NULL,
  `staff_reply`    longtext      NOT NULL,
  `staff_reply_at` datetime(6)   NULL,
  `helpful_count`  int unsigned  NOT NULL,
  `created_at`     datetime(6)   NOT NULL,
  `updated_at`     datetime(6)   NOT NULL,
  `customer_id`    bigint        NOT NULL,
  `event_id`       bigint        NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `services_eventreview_event_customer_uniq` (`event_id`, `customer_id`),
  KEY `services_eventreview_customer_id_idx` (`customer_id`),
  KEY `services_eventreview_event_id_idx`    (`event_id`),
  CONSTRAINT `services_eventreview_customer_id_fk`
    FOREIGN KEY (`customer_id`) REFERENCES `customer_customer` (`id`) ON DELETE CASCADE,
  CONSTRAINT `services_eventreview_event_id_fk`
    FOREIGN KEY (`event_id`)    REFERENCES `services_event`    (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `services_eventreviewhelpful` (
  `id`          bigint      NOT NULL AUTO_INCREMENT,
  `created_at`  datetime(6) NOT NULL,
  `customer_id` bigint      NOT NULL,
  `review_id`   bigint      NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `services_eventreviewhelpful_review_customer_uniq` (`review_id`, `customer_id`),
  KEY `services_eventreviewhelpful_customer_id_idx` (`customer_id`),
  KEY `services_eventreviewhelpful_review_id_idx`   (`review_id`),
  CONSTRAINT `services_eventreviewhelpful_customer_id_fk`
    FOREIGN KEY (`customer_id`) REFERENCES `customer_customer`    (`id`) ON DELETE CASCADE,
  CONSTRAINT `services_eventreviewhelpful_review_id_fk`
    FOREIGN KEY (`review_id`)   REFERENCES `services_eventreview` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
