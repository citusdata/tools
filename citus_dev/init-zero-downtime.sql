set citus.shard_count = 4;
CREATE TABLE tab (x int PRIMARY KEY);
SELECT create_distributed_table('tab','x');
INSERT INTO tab SELECT * from generate_series(1, 100);
