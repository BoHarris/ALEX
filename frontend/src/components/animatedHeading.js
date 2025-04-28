import { motion } from "framer-motion";

function AnimatedLoginSVG() {
  return (
    <svg viewBox="0 0 600 150" width="100%" height="150">
      <motion.text
        x="50%"
        y="60%"
        textAnchor="middle"
        fontSize="40"
        fill="#fff"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1.2 }}
      >
        Login to Alex.<tspan fill="#f87171">ai</tspan>
      </motion.text>
    </svg>
  );
}

export default AnimatedLoginSVG;
