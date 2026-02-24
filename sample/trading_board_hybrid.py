#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""Hybrid trading board bootstrap example (Redis + PostgreSQL)."""

import logging

from trading_ig import IGService
from trading_ig.config import config

from trading_board.config import TradingBoardConfig
from trading_board.consumer import TradingBoardConsumer
from trading_board.redis_client import RedisOrderSubscriber
from trading_board.store import PostgresOrderStore

logger = logging.getLogger(__name__)


def create_ig_service():
    ig_service = IGService(
        config.username,
        config.password,
        config.api_key,
        config.acc_type,
        acc_number=getattr(config, "acc_number", None),
    )
    ig_service.create_session()
    return ig_service


def main():
    logging.basicConfig(level=logging.INFO)
    board_config = TradingBoardConfig.from_env()

    store = PostgresOrderStore(
        dsn=board_config.postgres_dsn,
        create_tables_on_boot=board_config.create_tables_on_boot,
    )
    subscriber = RedisOrderSubscriber(
        redis_url=board_config.redis_url,
        channel=board_config.redis_channel,
    )
    ig_service = create_ig_service()
    consumer = TradingBoardConsumer(
        subscriber=subscriber,
        store=store,
        execution_service=ig_service,
    )

    logger.info("Listening on channel=%s", board_config.redis_channel)
    consumer.run_forever()


if __name__ == "__main__":
    main()
