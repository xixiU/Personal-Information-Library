import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import SourceList from './pages/SourceList'
import TaskList from './pages/TaskList'
import ResultDetail from './pages/ResultDetail'
import RefinedResultDetail from './pages/RefinedResultDetail'

const { Header, Content } = Layout

export default function App() {
  return (
    <BrowserRouter>
      <Layout style={{ minHeight: '100vh' }}>
        <Header>
          <div style={{ color: 'white', fontSize: 20, float: 'left', marginRight: 40 }}>
            个人信息库
          </div>
          <Menu theme="dark" mode="horizontal" defaultSelectedKeys={['sources']}>
            <Menu.Item key="sources">
              <Link to="/">信源管理</Link>
            </Menu.Item>
            <Menu.Item key="tasks">
              <Link to="/tasks">任务列表</Link>
            </Menu.Item>
            <Menu.Item key="results">
              <Link to="/results">采集结果</Link>
            </Menu.Item>
          </Menu>
        </Header>
        <Content>
          <Routes>
            <Route path="/" element={<SourceList />} />
            <Route path="/tasks" element={<TaskList />} />
            <Route path="/results" element={<ResultDetail />} />
            <Route path="/refined/:id" element={<RefinedResultDetail />} />
          </Routes>
        </Content>
      </Layout>
    </BrowserRouter>
  )
}
