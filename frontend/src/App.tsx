import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import { useState } from 'react'
import { DatabaseOutlined, UnorderedListOutlined, FileTextOutlined, ThunderboltOutlined, CheckCircleOutlined, TagsOutlined, SettingOutlined, BellOutlined, StarOutlined } from '@ant-design/icons'
import SourceList from './pages/SourceList'
import TaskList from './pages/TaskList'
import ResultDetail from './pages/ResultDetail'
import RefinedResultDetail from './pages/RefinedResultDetail'
import CategoryList from './pages/CategoryList'
import NotificationChannels from './pages/NotificationChannels'
import InterestPoints from './pages/InterestPoints'

const { Sider, Content } = Layout

function AppContent() {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  const menuItems = [
    {
      key: 'sources-parent',
      icon: <DatabaseOutlined />,
      label: '信源管理',
      children: [
        {
          key: 'sources',
          icon: <DatabaseOutlined />,
          label: <Link to="/">信源列表</Link>,
        },
        {
          key: 'categories',
          icon: <TagsOutlined />,
          label: <Link to="/categories">分类管理</Link>,
        },
      ],
    },
    {
      key: 'tasks',
      icon: <UnorderedListOutlined />,
      label: '任务管理',
      children: [
        {
          key: 'crawl-tasks',
          icon: <ThunderboltOutlined />,
          label: <Link to="/tasks/crawl">爬取任务</Link>,
        },
        {
          key: 'refine-tasks',
          icon: <CheckCircleOutlined />,
          label: <Link to="/tasks/refine">精炼任务</Link>,
        },
      ],
    },
    {
      key: 'results',
      icon: <FileTextOutlined />,
      label: <Link to="/results">采集结果</Link>,
    },
    {
      key: 'interest-points',
      icon: <StarOutlined />,
      label: <Link to="/interest-points">兴趣图谱</Link>,
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
      children: [
        {
          key: 'notification-channels',
          icon: <BellOutlined />,
          label: <Link to="/notification-channels">通知渠道</Link>,
        },
      ],
    },
  ]

  const getSelectedKeys = () => {
    const path = location.pathname
    if (path === '/') return ['sources']
    if (path === '/tasks/crawl') return ['crawl-tasks']
    if (path === '/tasks/refine') return ['refine-tasks']
    if (path === '/categories') return ['categories']
    if (path === '/results') return ['results']
    if (path === '/interest-points') return ['interest-points']
    if (path === '/notification-channels') return ['notification-channels']
    return []
  }

  const getOpenKeys = () => {
    const path = location.pathname
    if (path === '/' || path === '/categories') return ['sources-parent']
    if (path.startsWith('/tasks')) return ['tasks']
    if (path === '/notification-channels') return ['settings']
    return []
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={200}
        theme="light"
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: collapsed ? 14 : 18,
          fontWeight: 'bold',
          borderBottom: '1px solid #f0f0f0',
          overflow: 'hidden',
          whiteSpace: 'nowrap'
        }}>
          {collapsed ? '信息库' : '个人信息库'}
        </div>
        <Menu
          mode="inline"
          selectedKeys={getSelectedKeys()}
          defaultOpenKeys={getOpenKeys()}
          style={{ height: 'calc(100% - 64px)', borderRight: 0 }}
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Content style={{ background: '#f0f2f5' }}>
          <Routes>
            <Route path="/" element={<SourceList />} />
            <Route path="/tasks/crawl" element={<TaskList type="crawl" />} />
            <Route path="/tasks/refine" element={<TaskList type="refine" />} />
            <Route path="/categories" element={<CategoryList />} />
            <Route path="/results" element={<ResultDetail />} />
            <Route path="/interest-points" element={<InterestPoints />} />
            <Route path="/refined/:id" element={<RefinedResultDetail />} />
            <Route path="/notification-channels" element={<NotificationChannels />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  )
}
