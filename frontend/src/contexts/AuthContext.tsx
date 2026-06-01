import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface User {
  id: string
  username: string
  email?: string
  role: string
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  login: (username: string, password: string, remember?: boolean) => Promise<void>
  loginWithToken: (token: string, user: User) => void
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // 检查本地存储中是否有登录信息并向后端验证token
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // 优先从 localStorage 检查（记住我），再检查 sessionStorage（不记住）
        let token = localStorage.getItem('token')
        let userStr = localStorage.getItem('user')
        let storage: Storage = localStorage

        if (!token || !userStr) {
          // 如果 localStorage 中没有，检查 sessionStorage
          token = sessionStorage.getItem('token')
          userStr = sessionStorage.getItem('user')
          storage = sessionStorage
        }

        if (!token || !userStr) {
          setLoading(false)
          return
        }

        // 向后端验证token是否有效
        const response = await fetch('/api/auth/verify', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })

        if (response.ok) {
          // Token有效，使用storage中的用户信息
          const userData = JSON.parse(userStr)
          setUser(userData)
        } else {
          // Token无效或过期，清除所有存储
          console.warn('Token验证失败，清除登录状态')
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          sessionStorage.removeItem('token')
          sessionStorage.removeItem('user')
          setUser(null)
        }
      } catch (error) {
        console.error('认证检查失败:', error)
        // 网络错误或其他异常，清除所有登录状态
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        sessionStorage.removeItem('token')
        sessionStorage.removeItem('user')
        setUser(null)
      } finally {
        setLoading(false)
      }
    }

    checkAuth()
  }, [])

  const login = async (username: string, password: string, remember: boolean = false): Promise<void> => {
    try {
      // 选择存储方式：记住我使用 localStorage，否则使用 sessionStorage
      const storage: Storage = remember ? localStorage : sessionStorage

      // 模拟登录API调用
      // 在实际项目中，这里应该调用真实的API
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      })

      if (!response.ok) {
        // 如果后端还没有实现认证API，使用模拟登录
        if (response.status === 404) {
          // 模拟登录逻辑（仅用于开发）
          if (username === 'admin' && password === 'admin123') {
            const mockUser = {
              id: '1',
              username: 'admin',
              email: 'admin@example.com',
              role: 'admin'
            }
            const mockToken = 'mock-jwt-token-' + Date.now()

            // 使用选定的存储方式
            storage.setItem('token', mockToken)
            storage.setItem('user', JSON.stringify(mockUser))

            // 如果勾选"记住我"，保存用户名用于下次自动填充
            if (remember) {
              localStorage.setItem('rememberedUsername', username)
            }

            setUser(mockUser)

            console.log(`✅ 登录成功 - 存储方式: ${remember ? 'localStorage (记住我)' : 'sessionStorage (不记住)'}`)
            return
          } else {
            throw new Error('用户名或密码错误')
          }
        }
        throw new Error('登录失败')
      }

      const data = await response.json()

      // 使用选定的存储方式
      storage.setItem('token', data.token)
      storage.setItem('user', JSON.stringify(data.user))

      // 如果勾选"记住我"，保存用户名用于下次自动填充
      if (remember) {
        localStorage.setItem('rememberedUsername', username)
      }

      setUser(data.user)

      console.log(`✅ 登录成功 - 存储方式: ${remember ? 'localStorage (记住我)' : 'sessionStorage (不记住)'}`)
    } catch (error) {
      console.error('登录错误:', error)
      throw error
    }
  }

  const loginWithToken = (token: string, user: User) => {
    // SSO登录：直接使用token和用户信息，存储到localStorage（记住我）
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
    setUser(user)
    console.log('✅ SSO登录成功 - 存储方式: localStorage')
  }

  const logout = () => {
    // 清除所有存储的 token 和 user（localStorage 和 sessionStorage）
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    sessionStorage.removeItem('token')
    sessionStorage.removeItem('user')
    // 注意：保留 rememberedUsername，用于下次登录时自动填充
    setUser(null)
    console.log('✅ 已退出登录，清除所有存储（保留用户名）')
  }

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    login,
    loginWithToken,
    logout,
    loading,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
