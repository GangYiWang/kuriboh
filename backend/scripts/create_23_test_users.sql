-- 仅用于开发/测试数据库。
-- 创建 QQ 号 10001～10023，统一密码为 123456。
-- 10001 为赛事管理员，其余账号为普通选手。
--
-- 密码已使用项目相同的 Argon2id 算法生成哈希，数据库中不保存明文。
-- 脚本可重复执行；QQ 号、昵称或统一登录标识冲突时跳过对应账号，不覆盖已有用户。

BEGIN;

WITH test_accounts (qq_number, nickname, role) AS (
    VALUES
        ('10001', '测试01', 'TOURNAMENT_ADMIN'),
        ('10002', '测试02', 'PLAYER'),
        ('10003', '测试03', 'PLAYER'),
        ('10004', '测试04', 'PLAYER'),
        ('10005', '测试05', 'PLAYER'),
        ('10006', '测试06', 'PLAYER'),
        ('10007', '测试07', 'PLAYER'),
        ('10008', '测试08', 'PLAYER'),
        ('10009', '测试09', 'PLAYER'),
        ('10010', '测试10', 'PLAYER'),
        ('10011', '测试11', 'PLAYER'),
        ('10012', '测试12', 'PLAYER'),
        ('10013', '测试13', 'PLAYER'),
        ('10014', '测试14', 'PLAYER'),
        ('10015', '测试15', 'PLAYER'),
        ('10016', '测试16', 'PLAYER'),
        ('10017', '测试17', 'PLAYER'),
        ('10018', '测试18', 'PLAYER'),
        ('10019', '测试19', 'PLAYER'),
        ('10020', '测试20', 'PLAYER'),
        ('10021', '测试21', 'PLAYER'),
        ('10022', '测试22', 'PLAYER'),
        ('10023', '测试23', 'PLAYER')
)
INSERT INTO users (
    id,
    phone_number,
    qq_number,
    nickname,
    password_hash,
    qq_openid,
    role,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    NULL,
    test_accounts.qq_number,
    test_accounts.nickname,
    '$argon2id$v=19$m=65536,t=3,p=4$cSEkmmcyC75WKG/XUrH8yQ$xICSCWI09ShJ3W4uFx6M0NU2szXxwZm13/MuQk43Zuk',
    NULL,
    test_accounts.role,
    now(),
    now()
FROM test_accounts
ON CONFLICT DO NOTHING;

COMMIT;

SELECT qq_number, nickname, role
FROM users
WHERE qq_number BETWEEN '10001' AND '10023'
ORDER BY qq_number;
