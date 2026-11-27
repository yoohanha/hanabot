/* [2-1] 하나 AI 학원 웹 상호작용 */

// [3-3] 모든 페이지에 채팅 UI 자동 생성
function initializeChatUI() {
  // 이미 있으면 스킵
  if (document.getElementById('chatModal')) return;

  // 채팅 모달 생성
  const chatModalHtml = `
    <div class="chat-modal" id="chatModal">
      <div class="chat-container">
        <div class="chat-header">
          <div class="chat-title-box">
            <img src="assets/mark.png" alt="하나봇" class="chat-icon">
            <span class="chat-title">하나봇</span>
          </div>
          <button class="chat-close" id="chatClose">✕</button>
        </div>
        <div class="chat-messages" id="chatMessages">
        </div>
        <div class="chat-input-area">
          <input type="text" class="chat-input" id="chatInput" placeholder="질문을 입력하세요..." autocomplete="off">
          <button class="chat-send" id="chatSend">전송</button>
        </div>
      </div>
    </div>
  `;

  // HTML 추가 (floating buttons는 index.html에 이미 존재)
  document.body.insertAdjacentHTML('beforeend', chatModalHtml);

  // [3-3] 저장된 채팅 내용 복구
  loadChatHistory();
}

// [3-3] localStorage에 채팅 내용 저장
function saveChatHistory() {
  const chatMessages = document.getElementById('chatMessages');
  if (!chatMessages) return;

  const messages = [];
  chatMessages.querySelectorAll('.chat-message').forEach(msg => {
    const isBot = msg.classList.contains('bot');
    const content = msg.querySelector('.message-content')?.innerHTML || '';
    messages.push({
      type: isBot ? 'bot' : 'user',
      content: content
    });
  });

  localStorage.setItem('hanabotChatHistory', JSON.stringify(messages));
}

// [3-3] localStorage에서 채팅 내용 복구
function loadChatHistory() {
  const chatMessages = document.getElementById('chatMessages');
  if (!chatMessages) return;

  const savedHistory = localStorage.getItem('hanabotChatHistory');

  if (savedHistory) {
    try {
      const messages = JSON.parse(savedHistory);
      messages.forEach(msg => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${msg.type}`;
        msgDiv.innerHTML = `<div class="message-content">${msg.content}</div>`;
        chatMessages.appendChild(msgDiv);
      });
    } catch (e) {
      console.error('채팅 내용 복구 실패:', e);
      // 기본 메시지 표시
      showInitialChatMessage();
    }
  } else {
    // 처음 방문 시 기본 메시지 표시
    showInitialChatMessage();
  }
}

// [3-3] 초기 채팅 메시지 표시
function showInitialChatMessage() {
  const chatMessages = document.getElementById('chatMessages');
  if (!chatMessages) return;

  const botDiv = document.createElement('div');
  botDiv.className = 'chat-message bot';
  botDiv.innerHTML = `
    <div class="message-content">
      <img src="assets/brand/app_icon.png" alt="하나 AI 채팅봇" style="width: 40px; height: 40px; border-radius: 8px; margin-right: 10px; vertical-align: middle;">
      <span style="display: inline-block; vertical-align: middle;">안녕하세요! 하나 AI 학원 규정을 물어보세요.</span>
    </div>
  `;
  chatMessages.appendChild(botDiv);

  // [3-3] 초기 메시지 저장
  saveChatHistory();
}

// [3-3] 초기화 시 UI 생성
initializeChatUI();

// [3-3] 페이지 떠날 때 채팅 초기화
window.addEventListener('beforeunload', function() {
  localStorage.removeItem('hanabotChatHistory');
});

// [3-3] 마크다운을 HTML로 변환
function markdownToHtml(text) {
  if (!text) return '';
  // ** 굵게 ** → <strong>
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // - 목록 → • (단락 내)
  text = text.replace(/^- /gm, '• ');
  // \n\n → </p><p> (단락 나누기)
  const lines = text.split('\n\n');
  return lines.map(p => '<p>' + p.replace(/\n/g, '<br>') + '</p>').join('');
}

// [2-1] 시간표 데이터 (API에서 로드)
// [3-1] 새 커리큘럼 적용
let SCHEDULE_DATA = {
  0: { name: '일요일', morning: '휴원', afternoon: '휴원' },
  1: { name: '월요일', morning: 'AI 기초 소양 (101호)', afternoon: '생성형 AI 활용 (102호)' },
  2: { name: '화요일', morning: '프롬프트 엔지니어링 (101호)', afternoon: '바이브 코딩 (102호)' },
  3: { name: '수요일', morning: 'AI 업무 자동화·ERP (101호)', afternoon: 'Private LLM ① (102호)' },
  4: { name: '목요일', morning: 'Private LLM ② (101호)', afternoon: 'AI 에이전트 (102호)' },
  5: { name: '금요일', morning: '에이전틱 AI (101호)', afternoon: 'AI 윤리와 보안·프로젝트 (102호)' },
  6: { name: '토요일', morning: '휴원', afternoon: '휴원' }
};

// [2-1] API에서 시간표 로드
async function loadScheduleData() {
  try {
    const response = await fetch('/api/docs');
    const docs = await response.json();

    if (docs['시간표']) {
      // [3-1] RAG_PLAN.md의 시간표 데이터를 파싱 (새 커리큘럼)
      SCHEDULE_DATA = {
        0: { name: '일요일', morning: '휴원', afternoon: '휴원' },
        1: { name: '월요일', morning: docs['시간표']['월요일']?.split('\n')[0] || 'AI 기초 소양 (101호)', afternoon: '생성형 AI 활용 (102호)' },
        2: { name: '화요일', morning: docs['시간표']['화요일']?.split('\n')[0] || '프롬프트 엔지니어링 (101호)', afternoon: '바이브 코딩 (102호)' },
        3: { name: '수요일', morning: docs['시간표']['수요일']?.split('\n')[0] || 'AI 업무 자동화·ERP (101호)', afternoon: 'Private LLM ① (102호)' },
        4: { name: '목요일', morning: docs['시간표']['목요일']?.split('\n')[0] || 'Private LLM ② (101호)', afternoon: 'AI 에이전트 (102호)' },
        5: { name: '금요일', morning: docs['시간표']['금요일']?.split('\n')[0] || '에이전틱 AI (101호)', afternoon: 'AI 윤리와 보안·프로젝트 (102호)' },
        6: { name: '토요일', morning: '휴원', afternoon: '휴원' }
      };

      // 오늘의 수업 다시 표시
      displayTodayClass();
    }
  } catch (error) {
    console.log('시간표 로드 실패 (로컬 데이터 사용):', error);
  }
}

// 초기화
document.addEventListener('DOMContentLoaded', function() {
  console.log('하나 AI 학원 웹사이트 로드됨');

  // 메뉴 초기화
  initializeMenu();

  // [3-6] 로그인 버튼
  const loginBtn = document.querySelector('.btn-login');
  if (loginBtn) {
    loginBtn.addEventListener('click', function() {
      alert('수업용 데모 사이트라 로그인이 없어요.\n신청은 가상 학번으로 해요.\n예: HANA-001');
    });
  }

  // [3-6] 관리자 화면 접근
  const adminLink = document.createElement('a');
  adminLink.href = 'admin.html';
  adminLink.style.position = 'fixed';
  adminLink.style.bottom = '20px';
  adminLink.style.left = '20px';
  adminLink.style.fontSize = '12px';
  adminLink.style.color = '#999';
  adminLink.style.textDecoration = 'none';
  adminLink.textContent = '⚙️ 관리자';
  document.body.appendChild(adminLink);

  // 시간표 데이터 로드 (API에서)
  loadScheduleData();

  // 슬라이더 초기화
  initializeSlider();

  // 오늘의 수업 표시
  displayTodayClass();

  // 탭 초기화
  initializeTabs();

  // 떠 있는 버튼 초기화
  initializeFloatingButtons();

  // 채팅 초기화
  initializeChat();

  // 모달 초기화
  initializeModals();

  // 데이터 로드
  loadPageData();
});

// 메뉴 기능
function initializeMenu() {
  const hamburger = document.getElementById('hamburger');
  const nav = document.getElementById('nav');
  const navItems = document.querySelectorAll('.nav-item');

  hamburger.addEventListener('click', function() {
    hamburger.classList.toggle('active');
    nav.classList.toggle('active');
  });

  navItems.forEach(item => {
    const title = item.querySelector('.nav-title');
    title.addEventListener('click', function(e) {
      if (window.innerWidth <= 768) {
        e.preventDefault();
        item.classList.toggle('open');
      }
    });
  });

  window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
      hamburger.classList.remove('active');
      nav.classList.remove('active');
      navItems.forEach(item => item.classList.remove('open'));
    }
  });

  document.addEventListener('click', function(e) {
    if (window.innerWidth <= 768) {
      if (!e.target.closest('header')) {
        hamburger.classList.remove('active');
        nav.classList.remove('active');
        navItems.forEach(item => item.classList.remove('open'));
      }
    }
  });
}

// [2-1] 슬라이더 기능
function initializeSlider() {
  const slider = document.getElementById('slider');
  const prevBtn = document.getElementById('sliderPrev');
  const nextBtn = document.getElementById('sliderNext');
  const pauseBtn = document.getElementById('sliderPause');
  const currentSlideSpan = document.getElementById('currentSlide');

  let currentSlide = 1;
  let totalSlides = slider ? slider.children.length : 3;  // [디자인] 슬라이드 수를 자동으로 셈
  let isPlaying = true;
  let autoPlayInterval;

  function updateSlider() {
    const offset = (currentSlide - 1) * -100;
    slider.style.transform = `translateX(${offset}%)`;
    currentSlideSpan.textContent = currentSlide;
  }

  function nextSlide() {
    if (currentSlide < totalSlides) {
      currentSlide++;
    } else {
      currentSlide = 1;
    }
    updateSlider();
  }

  function prevSlide() {
    if (currentSlide > 1) {
      currentSlide--;
    } else {
      currentSlide = totalSlides;
    }
    updateSlider();
  }

  function startAutoPlay() {
    if (isPlaying) {
      autoPlayInterval = setInterval(nextSlide, 5000);
    }
  }

  function stopAutoPlay() {
    clearInterval(autoPlayInterval);
  }

  // 버튼 이벤트
  prevBtn.addEventListener('click', function() {
    prevSlide();
    stopAutoPlay();
    startAutoPlay();
  });

  nextBtn.addEventListener('click', function() {
    nextSlide();
    stopAutoPlay();
    startAutoPlay();
  });

  pauseBtn.addEventListener('click', function() {
    isPlaying = !isPlaying;
    pauseBtn.textContent = isPlaying ? '일시정지' : '재생';
    pauseBtn.classList.toggle('playing');

    if (isPlaying) {
      startAutoPlay();
    } else {
      stopAutoPlay();
    }
  });

  // 초기 설정
  updateSlider();
  startAutoPlay();
}

// [2-1] 오늘의 수업 표시
function displayTodayClass() {
  const today = new Date().getDay();
  const todayClassDiv = document.getElementById('todayClass');
  const todayData = SCHEDULE_DATA[today];

  if (today === 0 || today === 6) {
    todayClassDiv.innerHTML = '<p style="color: var(--color-text-light); font-style: italic;">오늘은 휴원입니다</p>';
  } else {
    todayClassDiv.innerHTML = `
      <div class="today-class-item">
        <div class="today-class-time">오전 09:30 ~ 12:30</div>
        <div class="today-class-name">${todayData.morning}</div>
      </div>
      <div class="today-class-item">
        <div class="today-class-time">오후 14:00 ~ 17:00</div>
        <div class="today-class-name">${todayData.afternoon}</div>
      </div>
    `;
  }
}

// [2-1] 탭 기능
function initializeTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      const tabName = this.dataset.tab;

      // 모든 버튼과 콘텐츠에서 active 제거
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      // 클릭된 탭 활성화
      this.classList.add('active');
      document.getElementById(tabName).classList.add('active');
    });
  });
}

// [2-1] 떠 있는 버튼
function initializeFloatingButtons() {
  // [3-3] floatHanabot은 initializeChat에서 처리

  // 스크롤 시 떠 있는 버튼 표시/숨김
  window.addEventListener('scroll', function() {
    if (window.scrollY > 300) {
      document.querySelector('.floating-buttons').style.display = 'flex';
    } else {
      document.querySelector('.floating-buttons').style.display = 'flex';
    }
  });
}

// [2-1] 채팅 기능
function initializeChat() {
  const chatModal = document.getElementById('chatModal');
  const chatInput = document.getElementById('chatInput');
  const chatSend = document.getElementById('chatSend');
  const chatClose = document.getElementById('chatClose');
  const chatMessages = document.getElementById('chatMessages');

  // 채팅 열기/닫기
  function toggleChat() {
    chatModal.classList.toggle('active');
    if (chatModal.classList.contains('active')) {
      chatInput.focus();
    }
  }

  // [3-3] 메뉴바 "하나봇에게 묻기" 버튼 (.btn-hanabot)
  const btnHanabot = document.querySelector('.btn-hanabot');
  if (btnHanabot) {
    btnHanabot.addEventListener('click', toggleChat);
  }

  // 메뉴 링크 "하나봇에게 묻기"
  const hanabotButtons = document.querySelectorAll('a[href*="?id=하나봇"]');
  hanabotButtons.forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      toggleChat();
    });
  });

  // [3-3] 떠 있는 하나봇 버튼
  const floatHanabotBtn = document.getElementById('floatHanabot');
  if (floatHanabotBtn) {
    floatHanabotBtn.addEventListener('click', toggleChat);
  }

  // 닫기 버튼
  chatClose.addEventListener('click', toggleChat);

  // [3-3] 외부 클릭 시 닫기 (채팅 열기 버튼들은 제외)
  document.addEventListener('click', function(e) {
    const isChatArea = chatModal.contains(e.target);
    const isFloatingBtn = e.target.closest('.floating-buttons');
    const isHanabotBtn = e.target.closest('.btn-hanabot');
    const isHanabotLink = e.target.closest('a[href*="?id=하나봇"]');

    if (!isChatArea && !isFloatingBtn && !isHanabotBtn && !isHanabotLink) {
      chatModal.classList.remove('active');
    }
  });

  // [5-5] 에이전트 메시지 전송
  async function sendAgentMessage(question, studentId) {
    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const approvalCard = document.getElementById('approvalCard');

    // 메시지 표시
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message user';
    msgDiv.innerHTML = `<div class="message-content">${escapeHtml(question)}</div>`;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    chatInput.value = '';

    // [5-5] 기다리는 동안 표시 (모델 호출이 20초 이상 걸릴 수 있음)
    const thinking = window.agentBubble('🤔 에이전트 팀이 일하는 중... (20초 이상 걸릴 수 있어요)');
    try {
      const res = await fetch('/api/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, student_id: studentId })
      });
      const data = await res.json();
      thinking.remove();
      window.agentThreadId = data.thread_id;
      window.renderAgentResult(data, studentId);
    } catch (err) {
      thinking.remove();
      window.agentBubble(`❌ 오류: ${err.message}`);
    }
  }

  // [3-1] 메시지 전송 (한글 입력 문제 해결)
  let isSending = false;
  async function sendMessage() {
    // 중복 전송 방지
    if (isSending) return;

    const message = chatInput.value.trim();
    if (!message) return;

    isSending = true;

    // [5-5] 에이전트 모드 체크 (window 에서 agentMode 확인)
    if (window.agentMode) {
      const studentId = document.getElementById('studentId')?.value.trim();
      if (!studentId) {
        alert('학번을 입력하세요.');
        isSending = false;
        return;
      }
      // 에이전트 모드 → /api/agent 호출
      await sendAgentMessage(message, studentId);
      isSending = false;
      return;
    }

    // 사용자 메시지 표시
    const userDiv = document.createElement('div');
    userDiv.className = 'chat-message user';
    userDiv.innerHTML = `<div class="message-content">${escapeHtml(message)}</div>`;
    chatMessages.appendChild(userDiv);

    // 입력창 초기화
    chatInput.value = '';

    // 자동 스크롤
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // [3-3] 메시지 저장
    saveChatHistory();

    // 서버에 메시지 전송
    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
      });

      const data = await response.json();
      const botReply = data.reply || '오류가 발생했습니다.';
      const sources = data.sources || [];

      // 봇 메시지 표시
      const botDiv = document.createElement('div');
      botDiv.className = 'chat-message bot';

      // [3-1] 근거 처리 (규정에 없는 경우 & 인사말 제외)
      let sourcesHtml = '';
      if (!botReply.includes('규정에 없는') && !botReply.includes('하나 AI 학원 규정을 물어보세요')) {
        // 근거 중복 제거 및 포맷팅
        const uniqueSources = [...new Set(sources)];

        if (uniqueSources.length > 0) {
          sourcesHtml = '<div class="chat-sources">';
          uniqueSources.forEach(src => {
            // "[# 제목 > ## 소제목]" 형식에서 제목과 소제목 추출
            const match = src.match(/\[# (.+?) > ## (.+?)\]/);
            if (match) {
              const title = match[1];
              const section = match[2];
              sourcesHtml += `<a href="page.html?id=${encodeURIComponent(title)}&section=${encodeURIComponent(section)}" class="chat-source-link">${title} > ${section}</a>`;
            }
          });
          sourcesHtml += '</div>';
        }
      }

      botDiv.innerHTML = `
        <div class="message-content">
          ${escapeHtml(botReply)}
          ${sourcesHtml}
        </div>
      `;
      chatMessages.appendChild(botDiv);

      // 자동 스크롤
      chatMessages.scrollTop = chatMessages.scrollHeight;

      // [3-3] 메시지 저장
      saveChatHistory();
    } catch (error) {
      console.error('채팅 오류:', error);
      const botDiv = document.createElement('div');
      botDiv.className = 'chat-message bot';
      botDiv.innerHTML = `<div class="message-content">오류가 발생했습니다.</div>`;
      chatMessages.appendChild(botDiv);

      // [3-3] 메시지 저장
      saveChatHistory();
    } finally {
      isSending = false;
    }
  }

  // 전송 버튼
  chatSend.addEventListener('click', sendMessage);

  // [3-1] Enter 키로 전송 (한글 조합 중 제외, keydown 사용)
  chatInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.isComposing && e.keyCode !== 229) {
      e.preventDefault();
      sendMessage();
    }
  });

  // 모바일 감지 및 풀스크린 모드
  function updateChatForMobile() {
    if (window.innerWidth <= 480) {
      chatModal.classList.add('mobile-fullscreen');
    } else {
      chatModal.classList.remove('mobile-fullscreen');
    }
  }

  updateChatForMobile();
  window.addEventListener('resize', updateChatForMobile);
}

// XSS 방지 함수
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

// 모달 기능
function initializeModals() {
  // 상담 신청 모달 추가 예정
}

// 데이터 로드 (data/RAG_PLAN.md에서 읽기)
function loadPageData() {
  // 나중에 API를 통해 data/RAG_PLAN.md 콘텐츠 로드
}

// ============================================================================
// [5-5] 에이전트 모드 로직
// ============================================================================

// [5-5] 전역 변수 (에이전트 모드, thread ID)
window.agentMode = false;
window.agentThreadId = null;

// [5-5] 채팅창에 하나봇 말풍선 하나 추가 (돌려줘서 나중에 지울 수 있게)
window.agentBubble = function(text) {
  const chatMessages = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = 'chat-message bot';
  div.innerHTML = `<div class="message-content" style="white-space: pre-line;">${escapeHtml(text)}</div>`;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
};

// [5-5] 서버 응답 처리: 멈춤이면 승인 카드 · 끝이면 답 · 오류면 오류 (조용히 멈춘 것처럼 보이지 않게)
window.renderAgentResult = function(data, studentId) {
  if (data.error) {
    window.agentBubble(`❌ 오류: ${data.error}`);
  } else if (data.status === 'approval_pending') {
    if (data.note) window.agentBubble(data.note);
    window.showApprovalCard(data, studentId);
  } else {
    window.agentBubble(data.final_answer || '응답이 비어 있어요');
  }
};

// [5-5] 승인 카드 표시 (전역 함수)
window.showApprovalCard = function(data, studentId) {
  const approvalCard = document.getElementById('approvalCard');
  const approvalAccept = document.getElementById('approvalAccept');
  const approvalReject = document.getElementById('approvalReject');
  const approvalEdit = document.getElementById('approvalEdit');
  const approvalDetails = document.getElementById('approvalDetails');
  const isCancel = data.type === 'cancellation';

  approvalCard.querySelector('div').textContent = isCancel ? '📋 예약 취소 승인 대기' : '📋 예약 승인 대기';
  approvalDetails.innerHTML = `
    ${isCancel ? `🔖 예약 번호: ${escapeHtml(data.reserve_id || '')}<br>` : ''}
    📅 날짜: ${escapeHtml(String(data.date || 'N/A'))}<br>
    🕐 시작: ${escapeHtml(String(data.start_time || 'N/A'))}<br>
    ⏱️ 이용: ${escapeHtml(String(data.duration || 'N/A'))}시간<br>
    🖥️ PC: ${escapeHtml(String(data.pc_number || 'N/A'))}번<br>
    👤 학번: ${escapeHtml(String(data.student_id || studentId))}
  `;
  approvalCard.style.display = 'block';
  approvalCard.scrollIntoView({ block: 'nearest' });

  // [5-5] 버튼은 한 번만 눌리게: 누르면 카드를 숨기고 버튼 연결을 끊음
  const handleApproval = async (response) => {
    approvalCard.style.display = 'none';
    approvalAccept.onclick = approvalReject.onclick = approvalEdit.onclick = null;
    const thinking = window.agentBubble(`⏳ "${response}" 처리 중...`);
    try {
      const res = await fetch('/api/agent/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: window.agentThreadId, response })
      });
      const result = await res.json();
      thinking.remove();
      window.renderAgentResult(result, studentId);   // 수정이면 새 카드가 다시 뜸
    } catch (err) {
      thinking.remove();
      window.agentBubble(`❌ 오류: ${err.message}`);
    }
  };

  approvalAccept.onclick = () => handleApproval('y');
  approvalReject.onclick = () => handleApproval('n');
  approvalEdit.onclick = () => {
    const editText = prompt('수정 내용 (예: 3시로, PC 2번으로, 6시간으로):');
    if (editText) handleApproval(editText);
  };
};

// [5-5] 에이전트 메시지 전송 (전역 함수)
async function sendAgentMessage(question, studentId) {
  const chatMessages = document.getElementById('chatMessages');
  const chatInput = document.getElementById('chatInput');

  // 메시지 표시
  const msgDiv = document.createElement('div');
  msgDiv.className = 'chat-message user';
  msgDiv.innerHTML = `<div class="message-content">${escapeHtml(question)}</div>`;
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  chatInput.value = '';

  try {
    const res = await fetch('/api/agent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, student_id: studentId })
    });

    const data = await res.json();
    window.agentThreadId = data.thread_id;

    // 에이전트 응답 표시
    if (data.final_answer) {
      const botMsg = document.createElement('div');
      botMsg.className = 'chat-message bot';
      botMsg.innerHTML = `<div class="message-content">${escapeHtml(data.final_answer)}</div>`;
      chatMessages.appendChild(botMsg);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Interrupt 감지: status="approval_pending" 반환 시 승인 카드 표시
    if (data.status === 'approval_pending') {
      window.showApprovalCard(data, studentId);
    }
  } catch (err) {
    const errMsg = document.createElement('div');
    errMsg.className = 'chat-message bot';
    errMsg.innerHTML = `<div class="message-content">❌ 오류: ${escapeHtml(err.message)}</div>`;
    chatMessages.appendChild(errMsg);
  }
}

(function initAgentMode() {
  const agentModeBar = document.getElementById('agentModeBar');
  const agentModeToggle = document.getElementById('agentModeToggle');
  const studentIdInput = document.getElementById('studentIdInput');
  const studentId = document.getElementById('studentId');
  const approvalCard = document.getElementById('approvalCard');

  // [5-5] 모든 페이지에서 에이전트 모드 바 표시
  agentModeBar.style.display = 'block';

  // [5-5] 에이전트 모드 토글
  agentModeToggle.addEventListener('change', () => {
    window.agentMode = agentModeToggle.checked;
    if (window.agentMode) {
      studentIdInput.style.display = 'block';
      studentId.focus();
    } else {
      studentIdInput.style.display = 'none';
      approvalCard.style.display = 'none';
    }
  });
})();

// 스크롤 감지
window.addEventListener('scroll', function() {
  // 헤더 고정 등 스크롤 이벤트 추가 예정
});
