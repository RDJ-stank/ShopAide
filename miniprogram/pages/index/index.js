const API_BASE = 'https://witness-boss-prohibited-rapid.trycloudflare.com'

Page({
  data: {
    messages: [],
    inputText: '',
    loading: false,
    scrollTo: '',
    chatHistory: []
  },

  onLoad() {
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
    return messages
  },

  async sendMessage() {
    const text = this.data.inputText.trim()
    if (!text || this.data.loading) return

    this.setData({ inputText: '', loading: true })
    this.addMessage('user', text)

    try {
      // 1. 提交任务
      const postRes = await this.wxPost('/api/chat', {
        input: text,
        chat_history: this.data.chatHistory
      })
      const taskId = postRes.data.task_id

      // 2. 轮询结果（最多等 60 秒）
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
        // 更新对话历史（给下轮用）
        const hist = [...this.data.chatHistory,
          { role: 'user', content: text },
          { role: 'assistant', content: output }
        ].slice(-10) // 最多保留 10 轮
        this.setData({ chatHistory: hist })
      } else {
        this.addMessage('assistant', '抱歉，请求超时。请稍后重试或联系人工客服。')
      }
    } catch (err) {
      console.error('wx.request 失败:', JSON.stringify(err))
      var msg = '抱歉，网络异常。'
      // 把具体错误信息也显示出来，方便排查
      if (err && err.errMsg) msg += ' [' + err.errMsg + ']'
      this.addMessage('assistant', msg)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 封装 wx.request 为 Promise
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
