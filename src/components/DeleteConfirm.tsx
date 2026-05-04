import React from 'react';

interface Props { onCancel: () => void; onConfirm: () => void; }

export function DeleteConfirm({ onCancel, onConfirm }: Props) {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="confirm-dialog" onClick={e => e.stopPropagation()}>
        <h3>确定要重新开始吗？</h3>
        <p>现在的聊天记录、设置和记忆都会被清除。<br />如果你想保留，可以先导出聊天记录。</p>
        <div className="confirm-buttons">
          <button className="btn-cancel" onClick={onCancel}>再想想</button>
          <button className="btn-confirm-delete" onClick={onConfirm}>确定删除</button>
        </div>
      </div>
    </div>
  );
}
