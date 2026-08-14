import type { RouteRecordRaw } from 'vue-router'

import HomeView from '@/views/HomeView.vue'
import PlaceholderView from '@/views/PlaceholderView.vue'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import QqCallbackView from '@/views/QqCallbackView.vue'
import ProfileView from '@/views/ProfileView.vue'
import BanlistListView from '@/views/BanlistListView.vue'
import BanlistDetailView from '@/views/BanlistDetailView.vue'
import AnnouncementListView from '@/views/AnnouncementListView.vue'
import AnnouncementDetailView from '@/views/AnnouncementDetailView.vue'
import AdminDashboardView from '@/views/AdminDashboardView.vue'
import AdminBanlistsView from '@/views/AdminBanlistsView.vue'
import AdminAnnouncementsView from '@/views/AdminAnnouncementsView.vue'
import TournamentListView from '@/views/TournamentListView.vue'
import TournamentDetailView from '@/views/TournamentDetailView.vue'
import AdminTournamentsView from '@/views/AdminTournamentsView.vue'
import AdminTournamentDetailView from '@/views/AdminTournamentDetailView.vue'
import ReportListView from '@/views/ReportListView.vue'
import ReportDetailView from '@/views/ReportDetailView.vue'
import MessagesView from '@/views/MessagesView.vue'
import MyTournamentsView from '@/views/MyTournamentsView.vue'
import AdminMessagesView from '@/views/AdminMessagesView.vue'
import AdminAuditView from '@/views/AdminAuditView.vue'

interface PlaceholderRoute {
  path: string
  name: string
  title: string
  description: string
  requiresAuth?: boolean
}

const placeholders: PlaceholderRoute[] = [
  { path: '/rules', name: 'rules', title: '比赛规则', description: '正式规则内容将在后续内容阶段接入。' },
]

export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: HomeView, meta: { title: '首页' } },
  { path: '/login', name: 'login', component: LoginView, meta: { title: '登录', guestOnly: true } },
  { path: '/register', name: 'register', component: RegisterView, meta: { title: '注册', guestOnly: true } },
  { path: '/login/qq/callback', name: 'qq-callback', component: QqCallbackView, meta: { title: 'QQ 授权' } },
  { path: '/profile', name: 'profile', component: ProfileView, meta: { title: '个人中心', requiresAuth: true } },
  { path: '/messages', name: 'messages', component: MessagesView, meta: { title: '消息中心', requiresAuth: true } },
  { path: '/my-tournaments', name: 'my-tournaments', component: MyTournamentsView, meta: { title: '我的赛事', requiresAuth: true } },
  { path: '/banlists', name: 'banlists', component: BanlistListView, meta: { title: '禁卡表' } },
  { path: '/banlists/:id', name: 'banlist-detail', component: BanlistDetailView, meta: { title: '禁卡表详情' } },
  { path: '/announcements', name: 'announcements', component: AnnouncementListView, meta: { title: '平台公告' } },
  { path: '/announcements/:id', name: 'announcement-detail', component: AnnouncementDetailView, meta: { title: '公告详情' } },
  { path: '/tournaments', name: 'tournaments', component: TournamentListView, meta: { title: '赛事中心' } },
  { path: '/tournaments/:id', name: 'tournament-detail', component: TournamentDetailView, meta: { title: '赛事详情' } },
  { path: '/tournaments/:id/matches', redirect: (to) => `/tournaments/${String(to.params.id)}` },
  { path: '/tournaments/:id/results', redirect: (to) => `/tournaments/${String(to.params.id)}` },
  { path: '/reports', name: 'reports', component: ReportListView, meta: { title: '赛事周报' } },
  { path: '/reports/:id', name: 'report-detail', component: ReportDetailView, meta: { title: '周报详情' } },
  { path: '/admin', name: 'admin', component: AdminDashboardView, meta: { title: '管理后台', requiresAdmin: true } },
  { path: '/admin/banlists', name: 'admin-banlists', component: AdminBanlistsView, meta: { title: '禁卡表管理', requiresAdmin: true } },
  { path: '/admin/announcements', name: 'admin-announcements', component: AdminAnnouncementsView, meta: { title: '公告管理', requiresAdmin: true } },
  { path: '/admin/messages', name: 'admin-messages', component: AdminMessagesView, meta: { title: '平台通知', requiresAdmin: true } },
  { path: '/admin/audit', name: 'admin-audit', component: AdminAuditView, meta: { title: '操作审计', requiresAdmin: true } },
  { path: '/admin/tournaments', name: 'admin-tournaments', component: AdminTournamentsView, meta: { title: '赛事管理', requiresAdmin: true } },
  { path: '/admin/tournaments/:id/:section(settings|registrations|matches|playoffs|decks-report|notifications|audit)', name: 'admin-tournament-detail', component: AdminTournamentDetailView, meta: { title: '单届赛事管理', requiresAdmin: true } },
  ...placeholders.map((route) => ({
    path: route.path,
    name: route.name,
    component: PlaceholderView,
    props: { title: route.title, description: route.description },
    meta: { title: route.title, requiresAdmin: route.path.startsWith('/admin'), requiresAuth: route.requiresAuth },
  })),
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: PlaceholderView,
    props: { eyebrow: '404', title: '页面不存在', description: '请检查地址或返回首页。' },
    meta: { title: '页面不存在' },
  },
]
