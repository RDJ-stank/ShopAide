const API_BASE = 'https://witness-boss-prohibited-rapid.trycloudflare.com'
const STORAGE_MSG_KEY = 'shopaide_messages'
const STORAGE_HIST_KEY = 'shopaide_chat_history'
const STORAGE_TIME_KEY = 'shopaide_last_active'
const SESSION_TTL_MS = 30 * 60 * 1000  // 30 分钟无操作自动清空

Page({
  data: {
    messages: [],
    inputText: '',
    loading: false,
    scrollTo: ''
  },

  onLoad() {
    // 从本地存储恢复会话（30 分钟内有效）
    const lastActive = wx.getStorageSync(STORAGE_TIME_KEY)
    if (lastActive && (Date.now() - lastActive < SESSION_TTL_MS)) {
      const savedMessages = wx.getStorageSync(STORAGE_MSG_KEY) || []
      const savedHistory = wx.getStorageSync(STORAGE_HIST_KEY) || []
      if (savedMessages.length > 0) {
        this.setData({
          messages: savedMessages,
          chatHistory: savedHistory,
          scrollTo: 'msg-' + (savedMessages.length - 1)
        })
        return
      }
    }
    // 新会话
    this.addMessage('assistant', '你好！我是谷雨，你的电商售后助手。\n\n我可以帮你查订单、退货、发票、售后政策等问题。\n直接输入即可开始。')
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value })
  },

  addMessage(role, content) {
    const msg = { id: Date.now(), role, content }
    const messages = [...this.data.messages, msg]
    this.setData({
      messages,
      scrollTo: 'msg-' + (messages.length - 1)
    })
    // 持久化消息列表
    wx.setStorageSync(STORAGE_MSG_KEY, messages)
    wx.setStorageSync(STORAGE_TIME_KEY, Date.now())
    return messages
  },

  // 清空会话
  clearHistory() {
    wx.removeStorageSync(STORAGE_MSG_KEY)
    wx.removeStorageSync(STORAGE_HIST_KEY)
    wx.removeStorageSync(STORAGE_TIME_KEY)
    this.setData({ messages: [], chatHistory: [], inputText: '' })
    this.addMessage('assistant', '会话已清空。有什么可以帮你的？')
  },

  async sendMessage() {
    const text = this.data.inputText.trim()
    if (!text || this.data.loading) return

    this.setData({ inputText: '', loading: true })
    this.addMessage('user', text)

    try {
      const postRes = await this.wxPost('/api/chat', {
        input: text,
        chat_history: this.data.chatHistory
      })
      const taskId = postRes.data.task_id

      let output = null
      for (let i = 0; i < 30; i++) {
        await this.sleep(2000)
        const getRes = await this.wxGet('/api/chat/' + taskId)
        if (getRes.data.ready) {
          output = getRes.data.output
          break
        }
      }

      if (output) {
        this.addMessage('assistant', output)
        // 持久化对话历史
        const hist = [...this.data.chatHistory,
          { role: 'user', content: text },
          { role: 'assistant', content: output }
        ].slice(-10)
        this.setData({ chatHistory: hist })
        wx.setStorageSync(STORAGE_HIST_KEY, hist)
      } else {
        this.addMessage('assistant', '抱歉，请求超时。请稍后重试或联系人工客服。')
      }
    } catch (err) {
      console.error('wx.request 失败:', JSON.stringify(err))
      var msg = '抱歉，网络异常。'
      if (err && err.errMsg) msg += ' [' + err.errMsg + ']'
      this.addMessage('assistant', msg)
    } finally {
      this.setData({ loading: false })
    }
  },

  wxPost(url, data) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: API_BASE + url,
        method: 'POST',
        header: { 'Content-Type': 'application/json' },
        data,
        success: resolve,
        fail: reject
      })
    })
  },

  wxGet(url) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: API_BASE + url,
        method: 'GET',
        success: resolve,
        fail: reject
      })
    })
  },

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
})
