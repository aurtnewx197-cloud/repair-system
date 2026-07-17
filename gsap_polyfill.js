
window.gsap = (function() {
  var E = {
    "power2.out": function(p) { return 1 - (1-p)*(1-p); },
    "back.out(1.5)": function(p) { var c=1.5; return 1+(c+1)*Math.pow(p-1,3)+c*Math.pow(p-1,2); },
    "back.out(1.3)": function(p) { var c=1.3; return 1+(c+1)*Math.pow(p-1,3)+c*Math.pow(p-1,2); }
  };
  
  function q(target) {
    if (typeof target === "string") return Array.from(document.querySelectorAll(target));
    if (target instanceof Element) return [target];
    if (target.length) return Array.from(target);
    return [target];
  }
  
  function applyStyle(el, prop, val) {
    if (prop === "opacity") { el.style.opacity = val; return; }
    if (prop === "x") { el.__gx = val; }
    else if (prop === "y") { el.__gy = val; }
    else if (prop === "scale") { el.__gs = val; }
    else if (prop === "className") { el.className = val || ""; return; }
    else if (prop === "textContent") { el.textContent = typeof val === "number" ? Math.round(val) : val; return; }
    else if (prop === "color") { el.style.color = val; return; }
    else if (prop === "background") { el.style.background = val; return; }
    else if (prop === "display") { el.style.display = val; return; }
    else if (prop === "top") { el.style.top = val; return; }
    else if (prop === "left") { el.style.left = val; return; }
    else if (prop === "strokeDasharray") { el.setAttribute("stroke-dasharray", val); return; }
    else if (prop === "strokeDashoffset") { el.setAttribute("stroke-dashoffset", val); return; }
    else if (prop === "transformOrigin") { el.style.transformOrigin = val; return; }
    else { try { el.style[prop] = val; } catch(e) {} return; }
    
    if (el.__gx || el.__gy || el.__gs) {
      el.style.transform = "translateX(" + (el.__gx||0) + "px) translateY(" + (el.__gy||0) + "px) scale(" + (el.__gs||1) + ")";
    }
  }
  
  function Tween(target, vars, dur) {
    this.tgts = q(target);
    this.vars = {};
    this.dur = dur || 1;
    var ease = "power2.out";
    for (var k in vars) { if (k === "ease") { ease = vars[k]; } else { this.vars[k] = vars[k]; } }
    this.ease = E[ease] || (function(p){return p;});
    this._sv = null;
  }
  
  Tween.prototype = {
    getStartValues: function() {
      if (this._sv) return;
      this._sv = [];
      for (var ti = 0; ti < this.tgts.length; ti++) {
        var el = this.tgts[ti];
        var sv = {};
        for (var k in this.vars) {
          var tv = this.vars[k];
          if (typeof tv === "number") {
            if (k === "opacity") sv[k] = parseFloat(el.style.opacity) || 0;
            else if (k === "x") sv[k] = el.__gx || 0;
            else if (k === "y") sv[k] = el.__gy || 0;
            else if (k === "scale") sv[k] = el.__gs || 1;
            else sv[k] = 0;
          } else { sv[k] = tv; }
        }
        this._sv.push(sv);
      }
    },
    render: function(time, start) {
      this.getStartValues();
      var prog = this.dur > 0 ? Math.max(0, Math.min(1, (time - start) / this.dur)) : 1;
      if (time < start) prog = 0;
      var ep = this.ease(prog);
      for (var ti = 0; ti < this.tgts.length; ti++) {
        var el = this.tgts[ti];
        var sv = this._sv[ti];
        for (var k in this.vars) {
          var tv = this.vars[k];
          if (typeof tv === "number") {
            var from = sv[k] || 0;
            applyStyle(el, k, from + (tv - from) * ep);
          } else if (ep >= 0.99) {
            applyStyle(el, k, tv);
          }
        }
      }
    }
  };
  
  function TL() {
    this.items = [];
    this.dur = 0;
    this.p = 0;
    this.cb = null;
  }
  
  TL.prototype = {
    add: function(tw, pos) {
      var start = this.dur;
      if (typeof pos === "number") start = pos;
      else if (typeof pos === "string") {
        var m = pos.match(/^\+=(.+)/);
        if (m) start = this.dur + parseFloat(m[1]);
        m = pos.match(/^-=(.+)/);
        if (m) start = Math.max(0, this.dur - parseFloat(m[1]));
      }
      tw.start = start;
      var end = start + tw.dur;
      if (end > this.dur) this.dur = end;
      this.items.push(tw);
      return this;
    },
    to: function(target, vars, dur, pos) {
      if (typeof dur === "string") { pos = dur; dur = 1; }
      return this.add(new Tween(target, vars, dur), pos);
    },
    fromTo: function(target, fromV, toV, dur, pos) {
      if (typeof dur === "string") { pos = dur; dur = 1; }
      var tgs = q(target);
      for (var i = 0; i < tgs.length; i++) {
        for (var k in fromV) applyStyle(tgs[i], k, fromV[k]);
      }
      var combined = {};
      for (var k in toV) combined[k] = toV[k];
      return this.add(new Tween(target, combined, dur), pos);
    },
    set: function(target, vars) {
      var tgs = q(target);
      for (var i = 0; i < tgs.length; i++) {
        for (var k in vars) applyStyle(tgs[i], k, vars[k]);
      }
      return this;
    },
    progress: function(v) {
      if (v === undefined) return this.p;
      this.p = Math.max(0, Math.min(1, v));
      var time = this.p * this.dur;
      for (var i = 0; i < this.items.length; i++) {
        var tw = this.items[i];
        tw.render(time, tw.start);
      }
      if (this.cb) this.cb();
      return this;
    },
    play: function() {},
    pause: function() {},
    totalDuration: function() { return this.dur; },
    eventCallback: function(name, fn) { if (name === "onUpdate") this.cb = fn; }
  };
  
  return { timeline: function() { return new TL(); } };
})();
