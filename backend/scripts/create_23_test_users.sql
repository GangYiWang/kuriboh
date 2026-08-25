-- 仅用于开发/测试数据库。
-- 创建 QQ 号 10001～10023，统一密码为 123456。
-- 10001 为平台管理员，其余账号为普通用户。
-- 需要先执行 Alembic 迁移至 20260825_0010 或更高版本。
--
-- 密码已使用项目相同的 Argon2id 算法生成哈希，数据库中不保存明文。
-- 脚本可重复执行；QQ 号、昵称或统一登录标识冲突时跳过对应账号，不覆盖已有用户。

BEGIN;

WITH test_accounts (qq_number, nickname, role) AS (
    VALUES
        ('10001', '测试01', 'PLATFORM_ADMIN'),
        ('10002', '测试02', 'USER'),
        ('10003', '测试03', 'USER'),
        ('10004', '测试04', 'USER'),
        ('10005', '测试05', 'USER'),
        ('10006', '测试06', 'USER'),
        ('10007', '测试07', 'USER'),
        ('10008', '测试08', 'USER'),
        ('10009', '测试09', 'USER'),
        ('10010', '测试10', 'USER'),
        ('10011', '测试11', 'USER'),
        ('10012', '测试12', 'USER'),
        ('10013', '测试13', 'USER'),
        ('10014', '测试14', 'USER'),
        ('10015', '测试15', 'USER'),
        ('10016', '测试16', 'USER'),
        ('10017', '测试17', 'USER'),
        ('10018', '测试18', 'USER'),
        ('10019', '测试19', 'USER'),
        ('10020', '测试20', 'USER'),
        ('10021', '测试21', 'USER'),
        ('10022', '测试22', 'USER'),
        ('10023', '测试23', 'USER')
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
