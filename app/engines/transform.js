// 變換題：作答形式與打字作答無異，引擎只是讓分派表完整（規格 §6.1 列四個引擎）。
import * as text from './text.js';

export const ENGINE = 'transform';

export const render = text.render;
