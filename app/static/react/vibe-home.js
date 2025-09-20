import{c as h,j as a,r as c}from"./chunks/client-DhEz86-d.js";/**
 * SparkleFall - Beautiful falling sparkle animations for your website
 * @version 1.0.0
 * @author Your Name
 * @license MIT
 */class d{constructor(t={}){this.config={container:document.body,interval:800,duration:5e3,sparkles:["✨","⭐","💫","🌟"],colors:null,minSize:10,maxSize:30,minDuration:2,maxDuration:5,wind:0,spin:!0,maxSparkles:50,autoStart:!0,zIndex:9999,injectStyles:!0,...t},this.sparkleContainer=null,this.intervalId=null,this.sparkleCount=0,this.isRunning=!1,this.init()}init(){if(typeof this.config.container=="string"&&(this.config.container=document.querySelector(this.config.container)),!this.config.container){console.error("SparkleFall: Container element not found");return}this.createContainer(),this.config.injectStyles&&this.injectStyles(),this.config.autoStart&&this.start()}createContainer(){this.sparkleContainer=document.createElement("div"),this.sparkleContainer.className="sparklefall-container",this.sparkleContainer.style.zIndex=this.config.zIndex,this.config.container.appendChild(this.sparkleContainer)}injectStyles(){if(document.getElementById("sparklefall-styles"))return;const t=`
      .sparklefall-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        overflow: hidden;
      }
      
      .sparklefall-sparkle {
        position: absolute;
        pointer-events: none;
        user-select: none;
        will-change: transform, opacity;
        filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.8));
      }
      
      @keyframes sparklefall-drop {
        to {
          transform: translateY(110vh) translateX(var(--wind-offset)) rotate(var(--rotation));
          opacity: 0;
        }
      }
      
      @keyframes sparklefall-drop-no-spin {
        to {
          transform: translateY(110vh) translateX(var(--wind-offset));
          opacity: 0;
        }
      }
    `,e=document.createElement("style");e.id="sparklefall-styles",e.textContent=t,document.head.appendChild(e)}createSparkle(){if(!this.sparkleContainer||this.sparkleCount>=this.config.maxSparkles)return;const t=document.createElement("div");t.className="sparklefall-sparkle";const e=this.config.sparkles[Math.floor(Math.random()*this.config.sparkles.length)];t.textContent=e,t.style.left=Math.random()*100+"%",t.style.top="-50px";const o=Math.random()*(this.config.maxSize-this.config.minSize)+this.config.minSize;if(t.style.fontSize=o+"px",this.config.colors&&this.config.colors.length>0){const f=this.config.colors[Math.floor(Math.random()*this.config.colors.length)];t.style.color=f}const s=Math.random()*(this.config.maxDuration-this.config.minDuration)+this.config.minDuration;t.style.animationDuration=s+"s";const l=this.config.spin?"sparklefall-drop":"sparklefall-drop-no-spin";t.style.animationName=l;const r=this.config.wind*100+"px",i=this.config.spin?Math.random()*720-360+"deg":"0deg";t.style.setProperty("--wind-offset",r),t.style.setProperty("--rotation",i),t.style.animationTimingFunction="linear",t.style.animationFillMode="forwards",this.sparkleContainer.appendChild(t),this.sparkleCount++,setTimeout(()=>{t.remove(),this.sparkleCount--},s*1e3)}start(){if(this.isRunning)return;this.isRunning=!0;const t=Math.min(5,this.config.maxSparkles);for(let e=0;e<t;e++)setTimeout(()=>this.createSparkle(),e*200);this.intervalId=setInterval(()=>{this.createSparkle()},this.config.interval)}stop(){this.isRunning&&(this.isRunning=!1,this.intervalId&&(clearInterval(this.intervalId),this.intervalId=null))}clear(){this.stop(),this.sparkleContainer&&this.sparkleContainer.querySelectorAll(".sparklefall-sparkle").forEach(e=>e.remove()),this.sparkleCount=0}destroy(){this.clear(),this.sparkleContainer&&(this.sparkleContainer.remove(),this.sparkleContainer=null)}updateConfig(t){this.config={...this.config,...t}}burst(t=10){const e=Math.min(t,this.config.maxSparkles-this.sparkleCount);for(let o=0;o<e;o++)setTimeout(()=>this.createSparkle(),o*50)}}function p(){return c.useEffect(()=>{const n=document.getElementById("sparkleContainer");if(!n)return;let t=null;try{const e=new d({container:n,sparkles:["✨","⭐","💫","🌟"],interval:800,maxSparkles:50,injectStyles:!0});t=e&&(e.destroy?e.destroy.bind(e):null)}catch{let o=function(){if(!s)return;const r=["✨","⭐","💫","🌟"],i=document.createElement("div");i.className="sparklefall-sparkle",i.textContent=r[Math.floor(Math.random()*r.length)],i.style.left=Math.random()*100+"%",i.style.animationDuration=Math.random()*3+2+"s",i.style.fontSize=Math.random()*20+10+"px",n.appendChild(i),setTimeout(()=>i.remove(),5e3)},s=!0;const l=setInterval(o,800);for(let r=0;r<5;r++)setTimeout(o,r*200);t=()=>{s=!1,clearInterval(l)}}return()=>{t&&t()}},[]),null}function u(){return c.useEffect(()=>{const n=document.getElementById("vibeCheckForm"),t=document.getElementById("analyzeBtn");if(!n||!t)return;function e(){t.classList.add("loading")}return n.addEventListener("submit",e),()=>n.removeEventListener("submit",e)},[]),null}function m(){return a.jsxs(a.Fragment,{children:[a.jsx(p,{}),a.jsx(u,{})]})}function k(n="react-home-root"){const t=document.getElementById(n);if(!t)return;h(t).render(a.jsx(m,{}))}if(typeof window<"u"){const n=()=>{document.getElementById("react-home-root")&&k("react-home-root")};document.readyState==="loading"?window.addEventListener("DOMContentLoaded",n):n()}
